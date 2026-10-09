"""Strict legacy-Jinja rendering plus Helm contract regression checks."""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "nextjs-java/web/skeleton"


def helper_fixture():
    required = ("p2p.mk", "p2p-build.mk", "scripts/build-image.sh")
    explicit = os.environ.get("P2P_HELPER_DIR")
    if explicit:
        fixture = pathlib.Path(explicit).resolve()
        if not all((fixture / file).is_file() for file in required):
            raise RuntimeError("P2P_HELPER_DIR must contain p2p.mk, p2p-build.mk and scripts/build-image.sh")
        return fixture
    # Locate the owning repository through Git, including a .worktrees checkout.
    # No workstation-specific path, and no synthetic helper substituted for it.
    common = pathlib.Path(subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=ROOT, text=True).strip())
    repository = (ROOT / common).resolve().parent
    sibling = repository.parent / "p2p"
    for fixture in (sibling / ".worktrees/local-development-workspaces", sibling):
        if all((fixture / file).is_file() for file in required):
            return fixture
    return None


def render(destination, name="notes-proof"):
    import jinja2
    env = jinja2.Environment(undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
    for source in SOURCE.rglob("*"):
        if any(part in {"node_modules", ".next", ".yarn", "build", ".gradle"} for part in source.relative_to(SOURCE).parts):
            continue
        if not source.is_file():
            continue
        target = pathlib.Path(destination) / source.relative_to(SOURCE)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            target.write_bytes(data)
        else:
            target.write_text(env.from_string(text).render(name=name, tenant="proof", version_prefix="", working_directory=""))
        shutil.copymode(source, target)


def test(require_helper=True):
    import yaml
    assert SOURCE.is_dir(), "Task9 nextjs-java skeleton does not exist"
    metadata = yaml.safe_load((SOURCE.parent / "template.yaml").read_text())
    assert metadata["kind"] == "app"
    assert metadata["config"]["ingress"]["enabled"] is False
    fixture = helper_fixture() if require_helper else None
    for name in ("a", "notes-proof", "zebra-service"):
        with tempfile.TemporaryDirectory(prefix="nextjs-java-render-") as tmp:
            render(tmp, name)
            base = pathlib.Path(tmp)
            manifest = json.loads((base / "frontend/package.json").read_text())
            for wrapper in ("gradlew", "gradlew.bat", "gradle/wrapper/gradle-wrapper.jar", "gradle/wrapper/gradle-wrapper.properties"):
                assert (base / "backend" / wrapper).is_file(), f"Missing backend Gradle wrapper: {wrapper}"
                reference = ROOT / "java/web/skeleton" / wrapper
                assert (SOURCE / "backend" / wrapper).read_bytes() == reference.read_bytes()
                if wrapper.endswith(".jar"):
                    assert (base / "backend" / wrapper).read_bytes() == reference.read_bytes()
                else:
                    # Jinja normalises CRLF (the upstream Windows script) to LF.
                    assert (base / "backend" / wrapper).read_text() == reference.read_text()
            assert "./gradlew build" in (base / "backend/Dockerfile").read_text()
            assert manifest["name"] == "app"
            assert '"app@workspace:.":' in (base / "frontend/yarn.lock").read_text()
            assert "--create-namespace" not in (base / "Makefile").read_text()
            makefile = (base / "Makefile").read_text()
            assert "P2P_HELPER_DIR" in makefile and "p2p-build-image" in makefile
            assert "$(P2P_APP_NAME)-frontend $(P2P_APP_NAME)-backend" in makefile
            assert "curl" not in makefile and "scale" not in makefile
            chart = base / "p2p/chart"
            archive = chart / "charts/core-platform-app-0.18.0.tgz"
            assert hashlib.sha256(archive.read_bytes()).hexdigest() == "2e85aedc9272c9fb861784e0b1c7f9529298f51f4721e36d8f8e3d1282e0f6eb"
            deps = yaml.safe_load((chart / "Chart.yaml").read_text())["dependencies"]
            assert {d["alias"] for d in deps} == {"frontend", "backend"}
            assert all(d["version"] == "0.18.0" for d in deps)
            output = subprocess.check_output(["helm", "template", name, str(chart), "--namespace", "supplied-namespace"], text=True)
            objects = [o for o in yaml.safe_load_all(output) if o]
            assert not any(o["kind"] == "Namespace" for o in objects)
            assert any(o["kind"] == "StatefulSet" and o["spec"]["volumeClaimTemplates"] for o in objects)
            deployments = [o for o in objects if o["kind"] == "Deployment"]
            assert len(deployments) == 2
            for obj in deployments:
                container = obj["spec"]["template"]["spec"]["containers"][0]
                is_frontend = obj["metadata"]["name"].endswith("frontend")
                env = container.get("env", [])
                secrets = [e for e in env if "secretKeyRef" in e.get("valueFrom", {})]
                assert bool(secrets) is not is_frontend
                probe = container["readinessProbe"]["httpGet"]
                assert probe["path"] == ("/readyz" if is_frontend else "/health")
            jobs = [o for o in objects if o["kind"] == "Job"]
            assert len(jobs) == 1 and jobs[0]["metadata"]["annotations"]["helm.sh/hook"] == "test"
            assert not any(o["kind"] == "HorizontalPodAutoscaler" for o in objects)
            for stage in ("functional", "integration", "extended-test", "prod"):
                stage_output = subprocess.check_output(["helm", "template", name, str(chart), "--namespace", "supplied-namespace", "-f", str(base / f"p2p/config/{stage}.yaml")], text=True)
                stage_jobs = [o for o in yaml.safe_load_all(stage_output) if o and o["kind"] == "Job"]
                assert len(stage_jobs) == (0 if stage == "prod" else 1)
                if stage_jobs:
                    assert stage_jobs[0]["metadata"]["name"].endswith("extended" if stage == "extended-test" else stage)
            missing = subprocess.run(["make", "-n", "p2p-build", "P2P_HELPER_DIR="], cwd=base, text=True, capture_output=True)
            assert missing.returncode != 0 and "reviewed local Task8 fixture" in missing.stderr
            if fixture is not None:
                common = [f"P2P_HELPER_DIR={fixture}", "P2P_IMAGE_CACHE_BACKEND=disabled", "P2P_VERSION=1.2.3"]
                dry = subprocess.check_output(["make", "-n", "p2p-functional", *common], cwd=base, text=True, stderr=subprocess.STDOUT)
                assert f"{name}-functional:1.2.3" in dry
                assert f'--namespace "proof-{name}-functional"' in dry
                assert "helm test" in dry and "--create-namespace" not in dry
                for stage, suffix in (("integration", "integration"), ("extended-test", "extended"), ("prod", "prod")):
                    dry = subprocess.check_output(["make", "-n", f"p2p-{stage}", *common], cwd=base, text=True, stderr=subprocess.STDOUT)
                    assert f'--namespace "proof-{name}-{suffix}"' in dry
                    assert f"{name}-frontend" in dry and f"{name}-backend" in dry
                    if stage != "prod":
                        assert f"{name}-{suffix}:1.2.3" in dry and "helm test" in dry
                inventory = subprocess.check_output(["make", "--no-print-directory", "p2p-images", *common], cwd=base, text=True)
                assert inventory.strip() == f"{name}-frontend {name}-backend"
            for component in ("frontend", "backend", "p2p/tests"):
                assert (base / component / "Dockerfile").is_file()
            runner = (base / "p2p/tests/run.mjs").read_text()
            assert "chromium.launch" in runner and "page.reload" in runner
            assert "TRUNCATE" not in runner.upper()
    print("Next.js/Java strict render and Helm structure checks passed (3 names)")
    if require_helper and fixture is None:
        raise RuntimeError("P2P helper stage contracts UNQUALIFIED: set P2P_HELPER_DIR to the reviewed Task8 fixture (or explicitly select --pure-render)")
    if fixture is not None:
        print(f"Actual P2P helper stage contracts passed: {fixture}")
    else:
        print("P2P helper stage contracts explicitly skipped / UNQUALIFIED (--pure-render)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--pure-render", action="store_true")
    parser.add_argument("--destination")
    args = parser.parse_args()
    if args.test:
        test()
    elif args.pure_render:
        test(require_helper=False)
    elif args.destination:
        render(args.destination)
    else:
        parser.error("--test or --destination is required")
