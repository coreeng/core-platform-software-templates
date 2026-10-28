import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('scan', Path(__file__).resolve().parents[2] / 'scripts/security/scan.py')
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


class ScanTests(unittest.TestCase):
    def test_inventory_covers_all_templates_and_images(self):
        items = scan.inventory()
        self.assertEqual(len(items), 11)
        self.assertEqual(sum(len(i['targets']) for i in items), 36)
        self.assertEqual(scan.inventory('infra/tofu')[0]['targets'], ['app'])
        with self.assertRaises(ValueError):
            scan.inventory('../invalid')

    def test_render_is_strict_preserves_binary_files_and_pins_build_helpers(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(scan, 'STATE', Path(temporary)):
            items = scan.inventory()
            scan.render(items)
            root = Path(temporary) / 'rendered'
            workflow = (root / 'nextjs-web/.github/workflows/fast-feedback.yaml').read_text()
            self.assertNotIn('{{ name }}', workflow)
            self.assertIn('${{ needs.version.outputs.version }}', workflow)
            self.assertIn(scan.CONFIG['p2p_commit'], (root / 'go-web/Makefile').read_text())
            original = scan.ROOT / 'java/web/skeleton/gradle/wrapper/gradle-wrapper.jar'
            self.assertEqual(original.read_bytes(), (root / 'java-web/gradle/wrapper/gradle-wrapper.jar').read_bytes())

    def test_failed_scanner_cannot_be_reported_as_clean(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(scan, 'REPORTS', Path(temporary)), \
                patch.object(scan, 'tool', side_effect=RuntimeError('missing scanner')), \
                patch.object(scan, 'base_report', return_value={'template': 'sample', 'target': 'source'}):
            result = scan.scan({'template': 'sample', 'slug': 'sample'}, 'source', Path(temporary))
            self.assertEqual(result['status'], 'failed')
            self.assertNotIn('blocking', result)
            self.assertEqual(scan.summary([result]), 2)

    def test_stale_build_fingerprint_rejected_before_scanning(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(scan, 'STATE', Path(temporary)), \
                patch.object(scan, 'REPORTS', Path(temporary) / 'reports'), patch.object(scan, 'scan') as scanner, \
                patch.object(scan, 'base_report', return_value={'template': 'sample', 'target': 'app'}):
            (Path(temporary) / 'builds.json').write_text(json.dumps([{'template': 'sample', 'target': 'app',
                'fingerprint': 'old', 'platform': scan.PLATFORM, 'status': 'complete'}]))
            results = scan.images([{'template': 'sample', 'slug': 'sample', 'targets': ['app'], 'fingerprint': 'new'}])
            scanner.assert_not_called()
            self.assertEqual(results[0]['status'], 'failed')

    def test_failure_and_finding_exit_codes_are_distinct(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(scan, 'REPORTS', Path(temporary)):
            record = {'template': 'sample', 'target': 'source', 'status': 'complete', 'blocking': 1}
            self.assertEqual(scan.summary([record]), 1)
            record['blocking'] = 0
            self.assertEqual(scan.summary([record]), 0)


if __name__ == '__main__':
    unittest.main()

class WorkflowTests(unittest.TestCase):
    def test_ci_calls_shared_targets_without_deployment_privileges(self):
        import yaml
        workflow = yaml.safe_load((scan.ROOT / '.github/workflows/security.yaml').read_text())
        self.assertEqual(workflow['permissions'], {'contents': 'read'})
        images = workflow['jobs']['images']
        self.assertFalse(images['strategy']['fail-fast'])
        self.assertEqual(images['strategy']['max-parallel'], 2)
        commands = [step.get('run', '') for step in images['steps']]
        self.assertIn('make security-build', commands)
        self.assertIn('make security-images', commands)
        uploads = [step for step in images['steps'] if step.get('uses', '').startswith('actions/upload-artifact@')]
        self.assertEqual(uploads[0]['if'], '${{ !cancelled() }}')
        self.assertNotIn('.security/\n', uploads[0]['with']['path'])

class EvidenceTests(unittest.TestCase):
    def test_container_environment_and_build_history_are_not_exported(self):
        evidence = scan.trivy_evidence({'SchemaVersion': 2,
            'Metadata': {'OS': {'Family': 'alpine'}, 'ImageConfig': {'Env': ['TOKEN=SENSITIVE']},
                         'History': [{'created_by': 'SENSITIVE'}]},
            'Results': [{'Target': 'package.lock', 'Packages': [{'Name': 'safe', 'Version': '1', 'BuildInfo': 'SENSITIVE'}]}]})
        self.assertNotIn('SENSITIVE', json.dumps(evidence))
        self.assertEqual(evidence['Results'][0]['Packages'][0]['Name'], 'safe')

class InstallerTests(unittest.TestCase):
    def test_mismatched_release_digest_never_installs_executable(self):
        module_spec = importlib.util.spec_from_file_location('installer', scan.ROOT / 'scripts/security/install.py')
        installer = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(installer)
        def download(args, **kwargs):
            Path(args[-1]).write_bytes(b'not the verified release')
        with tempfile.TemporaryDirectory() as temporary, patch.object(installer.platform, 'system', return_value='Linux'), \
                patch.object(installer.platform, 'machine', return_value='x86_64'), \
                patch.object(installer.subprocess, 'run', side_effect=download):
            with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                installer.install(Path(temporary))
            self.assertFalse((Path(temporary) / 'trivy').exists())

class CodeQLTests(unittest.TestCase):
    def test_creates_database_parent_and_writes_sarif_for_discovered_scopes(self):
        import sys
        import os
        module_spec = importlib.util.spec_from_file_location('codeql_runner', scan.ROOT / 'scripts/security/codeql.py')
        codeql = importlib.util.module_from_spec(module_spec)
        with patch.dict(sys.modules, {'scan': scan}):
            module_spec.loader.exec_module(codeql)
        calls = []
        def execute(args, **kwargs):
            calls.append(args)
            if args[2] == 'create':
                self.assertTrue(Path(args[3]).parent.is_dir())
            elif args[2] == 'analyze':
                Path(args[args.index('--output') + 1]).write_text('{"runs":[{"results":[]}]}')
        with tempfile.TemporaryDirectory() as temporary, patch.object(scan, 'STATE', Path(temporary)), \
                patch.object(scan, 'REPORTS', Path(temporary) / 'reports'), \
                patch.object(scan, 'output', return_value='{"version":"2.27.3"}'), \
                patch.object(scan, 'inventory', return_value=[{'template': 'fixture', 'slug': 'fixture'}]), \
                patch.object(scan, 'render'), patch.dict(os.environ, {'SECURITY_TEMPLATE': 'fixture'}), patch.object(scan, 'run', side_effect=execute), \
                patch.object(scan, 'base_report', return_value={'template': 'fixture', 'target': 'actions'}):
            (Path(temporary) / 'rendered/fixture/.github/workflows').mkdir(parents=True)
            self.assertEqual(codeql.main(), 0)
            self.assertEqual(len(calls), 2)
            self.assertIn('--build-mode', calls[0])
            self.assertIn('none', calls[0])
