"""Ordinary Docker smoke test. No Compose, host mounts, registry credentials or daemon changes.

Resources are created with a fresh nonce; only returned immutable IDs bearing that
nonce can be removed. All subprocesses have deadlines and cleanup runs in finally.
"""
import argparse
import contextlib
import hashlib
import json
import os
import pathlib
import platform
import signal
import subprocess
import sys
import tempfile
import time
import uuid
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "nextjs-java/web/skeleton"
LABEL = "io.coreeng.nextjs-java-proof"


class Interrupted(KeyboardInterrupt):
    """Unwind into resource cleanup on SIGINT/SIGTERM."""


@contextlib.contextmanager
def interruption_handlers(ignore=False):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    def interrupt(signum, _frame):
        raise Interrupted(f"Interrupted by signal {signum}")
    try:
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN if ignore else interrupt)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def command(args, env, timeout=120, capture=True, combine_stderr=False):
    """Every child has its own process group; cancellation reaps the whole group."""
    child = subprocess.Popen(args, env=env, text=True, start_new_session=True,
                             stdout=subprocess.PIPE if capture else None,
                             stderr=(subprocess.STDOUT if combine_stderr else subprocess.PIPE) if capture else None)
    try:
        output, errors = child.communicate(timeout=timeout)
    except BaseException:
        # Repeated signals must not abort cancellation or leave a child behind.
        with interruption_handlers(ignore=True):
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.communicate(timeout=5)
        raise
    if child.returncode:
        raise subprocess.CalledProcessError(child.returncode, args, output=output, stderr=errors)
    return (output or "").strip()


class Docker:
    def __init__(self, directory):
        self.nonce = str(uuid.uuid4())
        self.containers = []
        self.networks = []
        self.reservations = {kind: {} for kind in ("container", "network", "volume", "image")}
        self.env = dict(os.environ)
        config = pathlib.Path(directory) / "docker-config"
        config.mkdir()
        # Read daemon endpoint only. Never copy the user's authentication config.
        if not self.env.get("DOCKER_HOST"):
            self.env["DOCKER_HOST"] = command(
                ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
                self.env, timeout=30)
        self.env.pop("DOCKER_CONTEXT", None)
        self.env["DOCKER_CONFIG"] = str(config)
        plugin = pathlib.Path.home() / ".docker/cli-plugins"
        (config / "config.json").write_text(json.dumps({"cliPluginsExtraDirs": [str(plugin)]}))
        try:
            self.run("buildx", "version", timeout=30)
        except subprocess.CalledProcessError:
            if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
                raise RuntimeError("A working Docker buildx client plugin is required; host configuration was not changed")
            # Verified stable client-only fallback; never install into host config.
            url = "https://github.com/docker/buildx/releases/download/v0.38.0/buildx-v0.38.0.darwin-arm64"
            with urllib.request.urlopen(url, timeout=60) as response:
                binary = response.read()
            expected = "85989b895add5f119c1ccf8eada2f6892fc33ccf16bd8917638eae404ef26344"
            if hashlib.sha256(binary).hexdigest() != expected:
                raise RuntimeError("Temporary buildx client checksum mismatch")
            plugin_dir = config / "cli-plugins"
            plugin_dir.mkdir()
            executable = plugin_dir / "docker-buildx"
            executable.write_bytes(binary)
            executable.chmod(0o700)
            (config / "config.json").write_text("{}")
            self.run("buildx", "version", timeout=30)
        self.env["DOCKER_BUILDKIT"] = "1"

    def run(self, *args, timeout=120, capture=True):
        # Docker routes container stderr to the client's stderr. Combine only
        # logs; IDs, inspect JSON and daemon-error parsing remain stdout-only.
        return command(["docker", *args], self.env, timeout=timeout, capture=capture,
                       combine_stderr=args[:2] == ("container", "logs"))

    def inspect(self, kind, resource, timeout=120):
        try:
            records = json.loads(self.run(kind, "inspect", resource, timeout=timeout))
        except subprocess.CalledProcessError as error:
            # A daemon/auth/transport failure is not proof of nonexistence.
            message = (error.stderr or "").lower().strip()
            missing = (f"no such {kind}: {resource}".lower(),)
            if kind == "network":
                missing += (f"network {resource} not found".lower(),)
            if kind == "volume":
                missing += (f"get {resource}: no such volume".lower(),)
            if any(message.endswith(expected) for expected in missing):
                return None
            raise
        if len(records) != 1:
            raise RuntimeError(f"Ambiguous {kind} identity: {resource}")
        return records[0]

    def reserve(self, kind, name):
        if self.inspect(kind, name) is not None:
            raise RuntimeError(f"Refusing to adopt {kind}: {name} already exists")
        self.reservations[kind][name] = None

    def recover(self, kind, name, timeout=120):
        previous = self.reservations[kind][name]
        resource = previous if kind in ("container", "network") and previous is not None else name
        data = self.inspect(kind, resource, timeout=timeout)
        if data is None:
            return None
        labels = data.get("Config", {}).get("Labels", {}) if kind in ("container", "image") else data.get("Labels", {})
        if labels.get(LABEL) != self.nonce:
            raise RuntimeError(f"Refusing to touch unowned {kind} {name}")
        identifier = data.get("Id") if kind != "volume" else (data["Name"], data["CreatedAt"])
        if not identifier:
            raise RuntimeError(f"Missing {kind} identity: {name}")
        if previous is not None and previous != identifier:
            raise RuntimeError(f"Reserved {kind} identity changed: {name}")
        if kind in ("container", "network") and data.get("Name", "").lstrip("/") != name:
            raise RuntimeError(f"Reserved {kind} name changed: {name}")
        self.reservations[kind][name] = identifier
        return data

    def owned(self, kind, resource):
        data = self.inspect(kind, resource)
        if data is None:
            raise RuntimeError(f"Missing owned {kind}: {resource}")
        labels = data.get("Config", {}).get("Labels", {}) if kind in ("container", "image") else data.get("Labels", {})
        if labels.get(LABEL) != self.nonce:
            raise RuntimeError(f"Refusing to touch unowned {kind} {resource}")
        return data

    def build(self, component, context):
        tag = f"nextjs-java-proof-{self.nonce}-{component}:test"
        self.reserve("image", tag)
        # Reservation exists before any child starts. Failed/timed-out/interrupted
        # export is recovered by exact tag, label and immutable ID during cleanup.
        self.run("build", "--label", f"{LABEL}={self.nonce}", "--tag", tag,
                 "--build-arg", f"UNIT_TEST_NONCE={self.nonce}", str(context),
                 timeout=1800, capture=False)
        if self.recover("image", tag) is None:
            raise RuntimeError(f"Build returned without an owned image: {tag}")
        return tag

    def create_resource(self, kind, name):
        self.reserve(kind, name)
        returned = self.run(kind, "create", "--label", f"{LABEL}={self.nonce}", name)
        if kind != "volume":
            self.reservations[kind][name] = returned
        elif returned != name:
            raise RuntimeError(f"Volume creation identity mismatch: {name}")
        data = self.recover(kind, name)
        if data is None or (kind != "volume" and data["Id"] != returned):
            raise RuntimeError(f"{kind} creation identity mismatch: {name}")
        return returned

    def create(self, image, *args, aliases=()):
        name = f"nextjs-java-{self.nonce}-container-{len(self.reservations['container'])}"
        self.reserve("container", name)
        cid = self.run("container", "create", "--name", name, "--label", f"{LABEL}={self.nonce}",
                       "--network", self.networks[0],
                       *[part for alias in aliases for part in ("--network-alias", alias)],
                       *args, image)
        self.reservations["container"][name] = cid
        data = self.recover("container", name)
        if data is None or data["Id"] != cid:
            raise RuntimeError(f"Container creation identity mismatch: {name}")
        self.containers.append(cid)
        self.run("container", "start", cid)
        return cid

    def wait(self, cid, timeout=180):
        code = self.run("container", "wait", cid, timeout=timeout)
        print(self.run("container", "logs", cid), flush=True)
        if code != "0":
            raise RuntimeError(f"Container failed with exit code {code}")

    def cleanup(self):
        failures = []
        with interruption_handlers(ignore=True):
            for kind, names in self.reservations.items():
                # Separate budgets prevent an unresponsive container cleanup from
                # skipping network/volume/image cleanup. Child cancellation has
                # an additional bounded TERM/KILL grace period.
                deadline = time.monotonic() + 30
                for name in reversed(names):
                    try:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise RuntimeError(f"{kind} cleanup deadline exceeded: {name}")
                        data = self.recover(kind, name, timeout=min(5, remaining))
                        if data is None:
                            continue
                        identifier = names[name]
                        # Container/network removal is by immutable ID. Volumes
                        # have nonce labels plus a recorded creation fingerprint.
                        # Never force-delete an image ID and its unrelated tags.
                        target = name if kind in ("image", "volume") else identifier
                        options = ["--force", "--volumes"] if kind == "container" else []
                        self.run(kind, "rm", target, *options,
                                 timeout=min(5, max(0.1, deadline - time.monotonic())))
                    except Exception as error:
                        failures.append(str(error))
        if failures:
            raise RuntimeError("Cleanup incomplete: " + "; ".join(failures))


def wait_ready(docker, pg, backend, frontend):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            docker.run("exec", pg, "pg_isready", "-U", "notes", "-d", "notes", timeout=10)
            docker.run("exec", frontend, "node", "-e", "Promise.all(['http://backend:8081/health','http://backend:8081/prometheus','http://localhost:3000/readyz','http://localhost:8081/metrics'].map(async u=>{let r=await fetch(u);if(!r.ok)process.exit(1)})).catch(()=>process.exit(1))", timeout=10)
            return
        except subprocess.CalledProcessError:
            time.sleep(2)
    raise RuntimeError("Application readiness deadline exceeded")


def main(mode):
    with interruption_handlers(), tempfile.TemporaryDirectory(prefix="nextjs-java-docker-", dir=os.environ.get("TMPDIR")) as tmp:
        docker = Docker(tmp)
        try:
            tags = {}
            for name, context in (("frontend", SOURCE / "frontend"), ("backend", SOURCE / "backend"), ("functional", SOURCE / "p2p/tests"), ("integration", SOURCE / "p2p/tests"), ("extended", SOURCE / "p2p/tests")):
                tags[name] = docker.build(name, context)
            print("All five ordinary Docker images built; nonce-invalidated unit-test steps completed (see fresh test counts above)", flush=True)
            if mode == "build":
                return
            network = docker.create_resource("network", f"nextjs-java-{docker.nonce}-network")
            docker.networks.append(network)
            docker.owned("network", network)
            docker.run("pull", "docker.io/postgres:18.0-bookworm", timeout=300)
            volume = docker.create_resource("volume", f"nextjs-java-{docker.nonce}-data")
            password = str(uuid.uuid4())
            pg = docker.create("docker.io/postgres:18.0-bookworm", "--mount", f"type=volume,source={volume},target=/var/lib/postgresql", "-e", "POSTGRES_USER=notes", "-e", "POSTGRES_DB=notes", "-e", f"POSTGRES_PASSWORD={password}", aliases=("database",))
            backend = docker.create(tags["backend"], "-e", "DB_URL=jdbc:postgresql://database:5432/notes", "-e", "DB_USERNAME=notes", "-e", f"DB_PASSWORD={password}", aliases=("backend",))
            frontend = docker.create(tags["frontend"], "-e", "BACKEND_URL=http://backend:8080", aliases=("frontend",))
            wait_ready(docker, pg, backend, frontend)
            def browser(stage, *extra):
                cid = docker.create(tags[stage], "-e", "SERVICE_ENDPOINT=http://frontend:3000", "-e", "BACKEND_ENDPOINT=http://backend:8080", "-e", f"TEST_STAGE={stage}", *extra)
                docker.wait(cid)
            browser("functional", "-e", f"TEST_RUN_ID={docker.nonce}", "-e", "TEST_PRESERVE=true")
            # Restart the same immutable containers and database storage, not replace.
            for cid in (frontend, backend, pg):
                docker.owned("container", cid)
                docker.run("container", "stop", "--time", "20", cid)
            for cid in (pg, backend, frontend):
                docker.run("container", "start", cid)
            wait_ready(docker, pg, backend, frontend)
            browser("functional", "-e", f"TEST_RUN_ID={docker.nonce}", "-e", "TEST_MODE=verify")
            browser("integration")
            browser("extended")
            # Cleanup left no test-owned rows, confirmed via the real database.
            count = docker.run("exec", pg, "psql", "-U", "notes", "-d", "notes", "-tAc", "SELECT count(*) FROM notes")
            assert count == "0", f"Unexpected owned records remaining: {count}"
            print("Browser/API, Unicode boundaries, database and full application restart persistence passed", flush=True)
        except Exception:
            for cid in docker.containers:
                try:
                    print(docker.run("container", "logs", cid, timeout=5), flush=True)
                except Exception:
                    pass
            raise
        finally:
            original = sys.exception()
            try:
                docker.cleanup()
            except Exception as cleanup_error:
                if original is None:
                    raise
                original.add_note(str(cleanup_error))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("build", "functional"))
    main(parser.parse_args().mode)
