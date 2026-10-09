"""Offline failure-injection tests; never invoke Docker or fetch dependencies."""
import importlib.util
import io
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location("runner", pathlib.Path(__file__).with_name("nextjs_java_local.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
render_spec = importlib.util.spec_from_file_location("renderer", pathlib.Path(__file__).with_name("render_nextjs_java.py"))
renderer = importlib.util.module_from_spec(render_spec)
render_spec.loader.exec_module(renderer)


class FakeDocker(runner.Docker):
    def __init__(self, directory=None):
        self.nonce = "11111111-1111-4111-8111-111111111111"
        self.env = {}
        self.reservations = {kind: {} for kind in ("container", "network", "volume", "image")}
        self.objects = {}
        self.calls = []
        self.fail_build = None
        self.fail_create = None
        self.fail_cleanup = set()
        self.foreign_alias = None
        self.containers = []
        self.networks = []

    def run(self, *args, timeout=120, capture=True):
        self.calls.append(args)
        if args[0] == "build":
            tag = args[args.index("--tag") + 1]
            self.objects[("image", tag)] = {"Id": "sha256:" + "a" * 64, "RepoTags": [tag, "foreign:keep"], "Config": {"Labels": {runner.LABEL: self.nonce}}}
            self.objects[("image", "foreign:keep")] = self.objects[("image", tag)]
            if self.fail_build:
                raise self.fail_build
            return ""
        kind, operation, resource = args[:3]
        if operation == "inspect":
            if (kind, resource) not in self.objects:
                raise subprocess.CalledProcessError(1, args, stderr=f"No such {kind}: {resource}")
            return json.dumps([self.objects[(kind, resource)]])
        if operation == "rm":
            if kind in self.fail_cleanup:
                raise subprocess.TimeoutExpired(args, timeout)
            self.objects.pop((kind, resource), None)
            return ""
        if operation == "create":
            name = args[args.index("--name") + 1] if "--name" in args else args[-1]
            data = {"Id": "b" * 64, "Name": name, "Labels": {runner.LABEL: "foreign" if self.foreign_alias else self.nonce}}
            if kind == "volume":
                data["CreatedAt"] = "2026-10-09T00:00:00Z"
            if kind == "container":
                data["Config"] = {"Labels": data["Labels"]}
            self.objects[(kind, name)] = data
            self.objects[(kind, data["Id"])] = data
            if self.fail_create:
                raise self.fail_create
            return name if kind == "volume" else data["Id"]
        raise AssertionError(f"Unexpected fake command: {args}")

    def owned_object(self, kind, name, identifier=None):
        data = {"Id": identifier or name, "Name": name, "Labels": {runner.LABEL: self.nonce}}
        if kind == "volume":
            data["CreatedAt"] = "2026-10-09T00:00:00Z"
        if kind in ("container", "image"):
            data["Config"] = {"Labels": {runner.LABEL: self.nonce}}
        self.objects[(kind, name)] = data
        self.reservations[kind][name] = (name, data["CreatedAt"]) if kind == "volume" else data["Id"]


class LifecycleTests(unittest.TestCase):
    def test_failed_build_recovers_reserved_tag_and_preserves_foreign_tags(self):
        docker = FakeDocker()
        docker.fail_build = subprocess.CalledProcessError(1, ["docker", "build"])
        with self.assertRaises(subprocess.CalledProcessError):
            docker.build("frontend", pathlib.Path("frontend"))
        self.assertTrue(docker.reservations["image"])
        docker.cleanup()
        removals = [call for call in docker.calls if len(call) > 1 and call[1] == "rm"]
        self.assertEqual(len(removals), 1)
        self.assertNotIn("--force", removals[0])
        self.assertNotIn("foreign:keep", removals[0])
        self.assertNotIn("sha256:" + "a" * 64, removals[0])
        self.assertIn(("image", "foreign:keep"), docker.objects)

    def test_timed_out_and_interrupted_builds_are_recovered(self):
        for error in (subprocess.TimeoutExpired(["docker", "build"], 1), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                docker = FakeDocker()
                docker.fail_build = error
                with self.assertRaises(type(error)):
                    docker.build("backend", pathlib.Path("backend"))
                docker.cleanup()
                self.assertTrue(any(call[:2] == ("image", "rm") for call in docker.calls))

    def test_foreign_resources_refused_but_other_cleanup_stages_continue(self):
        docker = FakeDocker()
        docker.owned_object("container", "owned-container")
        docker.objects[("container", "owned-container")]["Config"]["Labels"][runner.LABEL] = "foreign"
        docker.owned_object("network", "owned-network")
        docker.owned_object("volume", "owned-volume")
        docker.owned_object("image", "owned-image")
        with self.assertRaisesRegex(RuntimeError, "unowned"):
            docker.cleanup()
        removals = [call for call in docker.calls if len(call) > 1 and call[1] == "rm"]
        self.assertFalse(any(call[0] == "container" for call in removals))
        self.assertEqual({call[0] for call in removals}, {"network", "volume", "image"})

    def test_cleanup_timeout_does_not_skip_other_stages(self):
        docker = FakeDocker()
        for kind in docker.reservations:
            docker.owned_object(kind, "owned-" + kind)
        docker.fail_cleanup = {"container"}
        with self.assertRaisesRegex(RuntimeError, "Cleanup incomplete"):
            docker.cleanup()
        self.assertEqual({call[0] for call in docker.calls if len(call) > 1 and call[1] == "rm"}, set(docker.reservations))

    def test_existing_network_is_not_adopted(self):
        docker = FakeDocker()
        name = "nextjs-java-" + docker.nonce + "-network"
        docker.objects[("network", name)] = {"Id": "foreign", "Labels": {runner.LABEL: "foreign"}}
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            docker.create_resource("network", name)
        self.assertFalse(any(call[:2] == ("network", "create") for call in docker.calls))
        self.assertFalse(docker.reservations["network"])

    def test_network_creation_race_never_removes_foreign_id(self):
        docker = FakeDocker()
        docker.foreign_alias = "race"
        with self.assertRaisesRegex(RuntimeError, "unowned"):
            docker.create_resource("network", "nextjs-java-" + docker.nonce + "-network")
        with self.assertRaisesRegex(RuntimeError, "unowned"):
            docker.cleanup()
        self.assertFalse(any(call[:2] == ("network", "rm") for call in docker.calls))

    def test_reserved_tag_rebound_to_other_id_is_refused(self):
        docker = FakeDocker()
        docker.owned_object("image", "owned-tag", "original-id")
        docker.objects[("image", "owned-tag")]["Id"] = "different-id"
        with self.assertRaisesRegex(RuntimeError, "identity changed"):
            docker.cleanup()
        self.assertFalse(any(call[:2] == ("image", "rm") for call in docker.calls))

    def test_fresh_unit_build_nonce_is_passed(self):
        docker = FakeDocker()
        docker.build("backend", pathlib.Path("backend"))
        command = next(call for call in docker.calls if call[0] == "build")
        self.assertIn("--build-arg", command)
        self.assertIn("UNIT_TEST_NONCE=" + docker.nonce, command)

    def test_main_finally_cleans_failed_timed_out_and_interrupted_builds(self):
        for error in (subprocess.CalledProcessError(1, ["fake"]), subprocess.TimeoutExpired("fake", 1), runner.Interrupted("SIGTERM")):
            with self.subTest(error=type(error).__name__):
                docker = FakeDocker()
                docker.fail_build = error
                with patch.object(runner, "Docker", return_value=docker), unittest.mock.patch("sys.stdout", new=io.StringIO()):
                    with self.assertRaises(type(error)):
                        runner.main("build")
                self.assertTrue(any(call[:2] == ("image", "rm") for call in docker.calls))

    def test_existing_volume_is_not_adopted(self):
        docker = FakeDocker()
        docker.owned_object("volume", "existing-volume")
        docker.reservations["volume"].clear()
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            docker.create_resource("volume", "existing-volume")
        self.assertFalse(docker.reservations["volume"])

    def test_volume_creation_fingerprint_change_is_refused(self):
        docker = FakeDocker()
        docker.owned_object("volume", "owned-volume")
        docker.objects[("volume", "owned-volume")]["CreatedAt"] = "different-time"
        with self.assertRaisesRegex(RuntimeError, "identity changed"):
            docker.cleanup()
        self.assertFalse(any(call[:2] == ("volume", "rm") for call in docker.calls))

    def test_ambiguous_inspect_result_is_not_adopted(self):
        docker = FakeDocker()
        with patch.object(docker, "run", return_value=json.dumps([{}, {}])):
            with self.assertRaisesRegex(RuntimeError, "Ambiguous"):
                docker.create_resource("network", "ambiguous")
        self.assertFalse(docker.reservations["network"])

    def test_daemon_error_is_not_treated_as_resource_absence(self):
        docker = FakeDocker()
        error = subprocess.CalledProcessError(1, ["fake"], stderr="daemon unavailable")
        with patch.object(docker, "run", side_effect=error):
            with self.assertRaises(subprocess.CalledProcessError):
                docker.reserve("image", "unsafe-tag")
        self.assertFalse(docker.reservations["image"])

    def test_network_cleanup_uses_recorded_id_even_if_name_becomes_ambiguous(self):
        docker = FakeDocker()
        name = "nextjs-java-" + docker.nonce + "-network"
        identifier = docker.create_resource("network", name)
        docker.objects[("network", name)] = {"Id": "foreign-id", "Labels": {runner.LABEL: "foreign"}}
        docker.cleanup()
        self.assertIn(("network", "rm", identifier), docker.calls)

    def test_interrupted_creates_recover_only_reserved_owned_identity(self):
        for kind in ("network", "volume", "container"):
            for error in (subprocess.TimeoutExpired("fake", 1), runner.Interrupted("SIGTERM")):
                with self.subTest(kind=kind, error=type(error).__name__):
                    docker = FakeDocker()
                    docker.fail_create = error
                    docker.networks = ["network-id"]
                    with self.assertRaises(type(error)):
                        if kind == "container":
                            docker.create("owned-image")
                        else:
                            docker.create_resource(kind, "nextjs-java-" + docker.nonce + "-" + kind)
                    self.assertEqual(len(docker.reservations[kind]), 1)
                    docker.cleanup()
                    self.assertTrue(any(call[:2] == (kind, "rm") for call in docker.calls))

    def test_actual_docker_missing_network_message_is_recognised(self):
        docker = FakeDocker()
        error = subprocess.CalledProcessError(1, ["fake"], stderr="Error response from daemon: network owned-network not found")
        with patch.object(docker, "run", side_effect=error):
            self.assertIsNone(docker.inspect("network", "owned-network"))

    def test_missing_daemon_socket_is_not_resource_absence(self):
        docker = FakeDocker()
        error = subprocess.CalledProcessError(1, ["fake"], stderr="Cannot connect to daemon: No such file or directory")
        with patch.object(docker, "run", side_effect=error):
            with self.assertRaises(subprocess.CalledProcessError):
                docker.reserve("image", "owned-tag")
        self.assertFalse(docker.reservations["image"])


class ChildProcessTests(unittest.TestCase):
    def test_container_logs_capture_both_streams_without_polluting_inspect_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = pathlib.Path(tmp) / "docker"
            executable.write_text('#!/bin/sh\nif [ "$1 $2" = "container logs" ]; then\n  printf "application stdout\\n"\n  printf "application stderr\\n" >&2\nelse\n  printf \'[{"Id":"owned-id"}]\\n\'\n  printf "diagnostic warning\\n" >&2\nfi\n')
            executable.chmod(0o700)
            docker = runner.Docker.__new__(runner.Docker)
            docker.env = dict(os.environ, PATH=tmp + os.pathsep + os.environ.get("PATH", ""))
            output = docker.run("container", "logs", "owned-id")
            self.assertIn("application stdout", output)
            self.assertIn("application stderr", output)
            self.assertEqual(json.loads(docker.run("container", "inspect", "owned-id")), [{"Id": "owned-id"}])

    def test_timeout_cancels_child_process_group_and_reaps(self):
        child = unittest.mock.Mock(pid=123)
        child.communicate.side_effect = [subprocess.TimeoutExpired("fake", 1), ("", "")]
        child.returncode = -15
        with patch.object(runner.subprocess, "Popen", return_value=child) as popen, patch.object(runner.os, "killpg") as kill:
            with self.assertRaises(subprocess.TimeoutExpired):
                runner.command(["fake"], {}, timeout=1)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        kill.assert_called_once_with(123, signal.SIGTERM)
        self.assertEqual(child.communicate.call_count, 2)

    def test_interruption_escalates_to_kill_if_child_ignores_term(self):
        child = unittest.mock.Mock(pid=321)
        child.communicate.side_effect = [KeyboardInterrupt(), subprocess.TimeoutExpired("fake", 5), ("", "")]
        with patch.object(runner.subprocess, "Popen", return_value=child), patch.object(runner.os, "killpg") as kill:
            with self.assertRaises(KeyboardInterrupt):
                runner.command(["fake"], {}, timeout=1)
        self.assertEqual(kill.call_args_list, [unittest.mock.call(321, signal.SIGTERM), unittest.mock.call(321, signal.SIGKILL)])

    def test_signal_handler_unwinds_finally_and_is_restored(self):
        handlers = []
        cleanup = []
        with patch.object(runner.signal, "getsignal", return_value="old"), patch.object(runner.signal, "signal", side_effect=lambda sig, handler: handlers.append((sig, handler))):
            with self.assertRaises(runner.Interrupted):
                with runner.interruption_handlers():
                    try:
                        next(handler for sig, handler in handlers if sig == signal.SIGTERM)(signal.SIGTERM, None)
                    finally:
                        cleanup.append("ran")
        self.assertEqual(cleanup, ["ran"])
        self.assertIn((signal.SIGTERM, "old"), handlers)


class HelperDiscoveryTests(unittest.TestCase):
    def test_explicit_incomplete_fixture_fails_instead_of_silently_skipping(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"P2P_HELPER_DIR": tmp}):
            with self.assertRaisesRegex(RuntimeError, "P2P_HELPER_DIR"):
                renderer.helper_fixture()

    def test_explicit_complete_fixture_is_returned_without_machine_specific_path(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"P2P_HELPER_DIR": tmp}):
            root = pathlib.Path(tmp)
            for relative in ("p2p.mk", "p2p-build.mk", "scripts/build-image.sh"):
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text("fixture")
            self.assertEqual(renderer.helper_fixture(), root.resolve())


class RenderGateTests(unittest.TestCase):
    def test_shell_forwards_pure_render_and_defaults_to_full_qualification(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = pathlib.Path(tmp) / "python"
            executable.write_text('#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\nprintf "%s\\n" "$@"\n')
            executable.chmod(0o700)
            env = dict(os.environ, NEXTJS_JAVA_TEST_PYTHON=str(executable), P2P_HELPER_DIR=str(pathlib.Path(tmp) / "missing-fixture"))
            script = pathlib.Path(__file__).with_name("nextjs_java_template_test.sh")
            pure = subprocess.check_output(["bash", str(script), "--pure-render"], env=env, text=True)
            self.assertEqual(pure.splitlines(), ["tests/render_nextjs_java.py", "--pure-render"])
            full = subprocess.check_output(["bash", str(script)], env=env, text=True)
            self.assertEqual(full.splitlines(), ["tests/render_nextjs_java.py", "--test"])

    def test_pure_structure_never_discovers_or_requires_fixture(self):
        class ReachedStructure(Exception):
            pass
        yaml = unittest.mock.Mock()
        yaml.safe_load.return_value = {"kind": "app", "config": {"ingress": {"enabled": False}}}
        with patch.dict(sys.modules, {"yaml": yaml}), patch.object(renderer, "helper_fixture", side_effect=RuntimeError("fixture unavailable")) as discover, patch.object(renderer, "render", side_effect=ReachedStructure):
            with self.assertRaises(ReachedStructure):
                renderer.test(require_helper=False)
        discover.assert_not_called()

    def test_full_qualification_fails_when_explicit_fixture_is_unavailable(self):
        yaml = unittest.mock.Mock()
        yaml.safe_load.return_value = {"kind": "app", "config": {"ingress": {"enabled": False}}}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"yaml": yaml}), patch.dict(os.environ, {"P2P_HELPER_DIR": str(pathlib.Path(tmp) / "missing-fixture")}):
            with self.assertRaisesRegex(RuntimeError, "P2P_HELPER_DIR"):
                renderer.test(require_helper=True)


if __name__ == "__main__":
    unittest.main()
