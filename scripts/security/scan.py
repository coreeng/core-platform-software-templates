#!/usr/bin/env python3
"""The same bounded, non-deploying template security runner for local use and CI."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / 'scripts/security/tools.json').read_text())
STATE = Path(os.environ.get('SECURITY_DIR', ROOT / '.security')).resolve()
TOOLS = Path(os.environ.get('SECURITY_TOOLS_DIR', STATE / 'tools')).resolve()
REPORTS = STATE / 'reports'
THRESHOLD = (os.environ.get('SECURITY_BLOCKING_SEVERITY') or 'high')
PLATFORM = (os.environ.get('SECURITY_PLATFORM') or ('linux/arm64' if platform.machine() in ('arm64', 'aarch64') else 'linux/amd64'))
TIMEOUT = int(os.environ.get('SECURITY_TIMEOUT', '1800'))


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, timeout=TIMEOUT, **kwargs)


def output(args, **kwargs):
    return run(args, stdout=subprocess.PIPE, text=True, **kwargs).stdout.strip()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def tracked():
    return sorted(set(output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT).splitlines()))


def inventory(selected=''):
    files = tracked()
    definitions = [p for p in files if p.endswith('/template.yaml') and len(Path(p).parts) <= 3]
    names = sorted(str(Path(p).parent) for p in definitions)
    if selected and selected not in names:
        raise ValueError(f'Unknown template: {selected}')
    result = []
    for name in names:
        if selected and selected != name:
            continue
        prefix = name + '/skeleton/'
        sources = [p for p in files if p.startswith(prefix)]
        dockerfiles = [p[len(prefix):] for p in sources if Path(p).name == 'Dockerfile']
        targets = []
        for dockerfile in dockerfiles:
            if dockerfile == 'Dockerfile':
                target = 'app'
            elif re.fullmatch(r'p2p/tests/[^/]+/Dockerfile', dockerfile):
                target = dockerfile.split('/')[2]
                target = 'extended-test' if target == 'extended' else target
            else:
                raise ValueError(f'Unmapped Dockerfile: {name}/{dockerfile}')
            # Reject Make's build-% fallback: it can succeed without building anything.
            makefile = (ROOT / prefix / 'Makefile').read_text()
            if not re.search(r'^build-' + re.escape(target) + r':', makefile, re.M):
                raise ValueError(f'Missing concrete build-{target} in {name}')
            targets.append(target)
        digest = hashlib.sha256()
        for source in sources:
            file = ROOT / source
            if file.is_symlink():
                raise ValueError(f'Symlinks are not supported in skeletons: {source}')
            digest.update(source.encode() + b'\0' + str(file.stat().st_mode & 0o777).encode() + b'\0' + file.read_bytes())
        result.append({'template': name, 'slug': name.replace('/', '-'), 'targets': sorted(targets),
                       'fingerprint': digest.hexdigest(), 'files': sources})
    if not result:
        raise ValueError('No templates discovered')
    return result


def render(items):
    from jinja2 import Environment, StrictUndefined
    environment = Environment(undefined=StrictUndefined, keep_trailing_newline=True)
    for item in items:
        dest = STATE / 'rendered' / item['slug']
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        prefix = item['template'] + '/skeleton/'
        for source in item['files']:
            source_path = ROOT / source
            target = dest / source[len(prefix):]
            target.parent.mkdir(parents=True, exist_ok=True)
            data = source_path.read_bytes()
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                target.write_bytes(data)
            else:
                text = environment.from_string(text).render(name='security-' + item['slug'], tenant='security', version_prefix='', working_directory='')
                # Generated builds otherwise fetch mutable P2P v1 during Make parsing.
                if target == dest / 'Makefile':
                    text = text.replace('https://raw.githubusercontent.com/coreeng/p2p/v1/p2p.mk',
                                        f'https://raw.githubusercontent.com/coreeng/p2p/{CONFIG["p2p_commit"]}/p2p.mk')
                target.write_text(text)
            target.chmod(source_path.stat().st_mode & 0o777)
    write(STATE / 'inventory.json', [{k: v for k, v in x.items() if k != 'files'} for x in items])


def tool(name):
    exe = TOOLS / name
    if not exe.is_file():
        raise RuntimeError(f'Missing {name}; run make security-tools')
    version = output([exe, '--version'], stderr=subprocess.STDOUT)
    if CONFIG['versions'][name] not in version:
        raise RuntimeError(f'Unexpected {name} version; run make security-tools')
    return exe


def base_report(item, target):
    runner_digest = hashlib.sha256()
    for source in sorted((ROOT / 'scripts/security').rglob('*')):
        if source.is_file() and '__pycache__' not in source.parts:
            runner_digest.update(str(source.relative_to(ROOT)).encode() + b'\0' + source.read_bytes())
    return {'template': item['template'], 'target': target, 'fingerprint': item['fingerprint'],
            'commit': output(['git', 'rev-parse', 'HEAD'], cwd=ROOT), 'platform': PLATFORM,
            'timestamp': datetime.now(timezone.utc).isoformat(), 'tools': CONFIG['versions'],
            'p2p_commit': CONFIG['p2p_commit'], 'includes_unfixed': True,
            'runner_fingerprint': runner_digest.hexdigest(),
            'dirty_checkout': bool(output(['git', 'status', '--porcelain'], cwd=ROOT))}


def trivy_evidence(raw):
    # ImageConfig/History can contain credentials even in a vulnerability-only scan.
    # Keep package/advisory evidence without exporting container environment or commands.
    evidence = {key: raw[key] for key in ('SchemaVersion', 'CreatedAt', 'ArtifactType') if key in raw}
    evidence['Metadata'] = {key: raw.get('Metadata', {})[key] for key in ('OS', 'ImageID', 'RepoDigests')
                            if key in raw.get('Metadata', {})}
    evidence['Results'] = []
    for result in raw.get('Results', []):
        exported = {key: result[key] for key in ('Target', 'Class', 'Type', 'Vulnerabilities', 'Licenses') if key in result}
        if 'Packages' in result:
            exported['Packages'] = [{key: package[key] for key in ('ID', 'Name', 'Version', 'Licenses') if key in package}
                                    for package in result['Packages']]
        evidence['Results'].append(exported)
    return evidence


def scan(item, target, workspace, image=None, history=False):
    report_path = REPORTS / item['slug'] / f'{target}.json'
    record = base_report(item, target)
    (report_path.parent / f'{target}-trivy.json').unlink(missing_ok=True)
    write(report_path, {**record, 'status': 'running'})
    phase = 'tool-preflight'
    print(f'Scan {item["template"]} {target}', flush=True)
    try:
        trivy, hog = tool('trivy'), tool('trufflehog')
        # Raw secrets, image archives and scanner stderr never enter uploaded reports.
        with tempfile.TemporaryDirectory(prefix='template-security-') as temporary:
            private = Path(temporary)
            trivy_json, secrets_json = private / 'trivy.json', private / 'secrets.jsonl'
            if image is not None:
                record['image'] = image['id']
                record['platform'] = image['platform']
                if not image['layers']:
                    # The monitoring app is FROM scratch, with no filesystem to inspect.
                    record.update(status='not-applicable', reason='Image has no filesystem layers', blocking=0)
                    write(report_path, record)
                    return record
                archive = private / 'image.tar'
                run(['docker', 'image', 'save', '--output', archive, image['id']], stdout=subprocess.DEVNULL)
                trivy_args = ['image', '--input', archive, '--scanners', 'vuln']
                hog_args = ['docker', '--image', archive.as_uri()]
            elif history:
                trivy_json.write_text('{"SchemaVersion":2,"Results":[]}')
                trivy_args = None
                hog_args = ['git', ROOT.as_uri(), '--branch', 'HEAD']
                base = os.environ.get('SECURITY_BASE')
                if base:
                    # Resolve before handing user-provided ref to a scanner argument.
                    base = output(['git', 'rev-parse', '--verify', base + '^{commit}'], cwd=ROOT)
                    hog_args += ['--since-commit', base]
                record['scope'] = f'{base}..HEAD' if base else 'HEAD history'
            else:
                trivy_args = ['fs', '--scanners', 'vuln,license', '.']
                hog_args = ['filesystem', str(workspace)]
            with (private / 'stderr').open('wb') as errors:
                if trivy_args is not None:
                    phase = 'trivy'
                    run([trivy, *trivy_args, '--format', 'json', '--exit-code', '0', '--ignorefile', '',
                         '--severity', 'UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL', '--timeout', f'{TIMEOUT}s',
                         '--cache-dir', STATE / 'cache/trivy', '--output', trivy_json], cwd=workspace,
                        stdout=subprocess.DEVNULL, stderr=errors)
                phase = 'trufflehog'
                with secrets_json.open('wb') as raw:
                    run([hog, *hog_args, '--json', '--no-update', '--results=verified,unverified,unknown'],
                        stdout=raw, stderr=errors, cwd=workspace)
            options = {'workspace': str(workspace), 'threshold': THRESHOLD, 'image': target if image else None}
            write(private / 'options.json', options)
            normalized = private / 'normalized.json'
            phase = 'report-validation'
            run(['node', ROOT / 'scripts/security/report.cjs', trivy_json, secrets_json, normalized, private / 'options.json'])
            record.update(json.loads(normalized.read_text()))
            # Retain full vulnerability/license evidence, never the unredacted secret stream.
            write(REPORTS / item['slug'] / f'{target}-trivy.json', trivy_evidence(json.loads(trivy_json.read_text())))
    except (subprocess.SubprocessError, OSError, ValueError, RuntimeError) as error:
        # Subprocess exceptions can contain secret output; retain only the error type/status.
        record.update(status='failed', error=type(error).__name__, phase=phase, exit_code=getattr(error, 'returncode', None))
        print(f'FAILED {item["template"]} {target}: {type(error).__name__}', flush=True)
    write(report_path, record)
    return record


def build(items):
    records = []
    write(STATE / 'builds.json', records)
    for item in items:
        workspace = STATE / 'rendered' / item['slug']
        for target in item['targets']:
            record = base_report(item, target)
            instance = hashlib.sha256(str(STATE).encode()).hexdigest()[:8]
            image = f'template-security/{instance}/{item["slug"]}-{target}:{item["fingerprint"][:12]}-{PLATFORM.split("/")[1]}'
            log = STATE / 'logs' / item['slug'] / f'{target}-build.log'
            log.parent.mkdir(parents=True, exist_ok=True)
            print(f'Build {item["template"]} {target}', flush=True)
            try:
                with log.open('w') as stream:
                    run(['make', f'build-{target}', 'P2P_VERSION=security', f'p2p_image_tag={image}',
                         f'p2p_image_cache=--pull --load --platform {PLATFORM}'], cwd=workspace,
                        stdout=stream, stderr=subprocess.STDOUT,
                        env={**os.environ, 'DOCKER_DEFAULT_PLATFORM': PLATFORM})
                info = json.loads(output(['docker', 'image', 'inspect', image]))[0]
                actual_platform = f'{info["Os"]}/{info["Architecture"]}'
                if actual_platform != PLATFORM:
                    raise RuntimeError('Built image platform does not match requested platform')
                record.update(status='complete', tag=image, id=info['Id'], platform=actual_platform,
                              layers=info.get('RootFS', {}).get('Layers', []))
            except (subprocess.SubprocessError, OSError, ValueError, RuntimeError) as error:
                record.update(status='failed', error=type(error).__name__)
                print(f'FAILED build {item["slug"]}/{target}; see {log}', flush=True)
            records.append(record)
            write(STATE / 'builds.json', records)
    return records


def images(items):
    records = json.loads((STATE / 'builds.json').read_text())
    results = []
    for item in items:
        for target in item['targets']:
            matches = [r for r in records if r['template'] == item['template'] and r['target'] == target
                       and r['fingerprint'] == item['fingerprint'] and r['platform'] == PLATFORM and r['status'] == 'complete']
            if len(matches) != 1:
                record = {**base_report(item, target), 'status': 'failed', 'error': 'Missing or stale successful build'}
                write(REPORTS / item['slug'] / f'{target}.json', record)
                results.append(record)
                continue
            results.append(scan(item, target, STATE / 'rendered' / item['slug'], image=matches[0]))
    return results


def summary(results, name='summary'):
    failed = sum(r['status'] == 'failed' for r in results)
    blockers = sum(r.get('blocking', 0) for r in results)
    report = {'status': 'failed' if failed else 'complete', 'blocking': blockers, 'scanner_failures': failed,
              'threshold': THRESHOLD, 'results': results}
    # Save DB metadata so later runs can explain differences as advisories change.
    metadata = STATE / 'cache/trivy/db/metadata.json'
    if metadata.exists():
        report['trivy_database'] = json.loads(metadata.read_text())
    write(REPORTS / f'{name}.json', report)
    lines = ['# Template security results', '', f'Blocking severity: {THRESHOLD}. Includes unfixed vulnerabilities.', '',
             '| Template | Target | Status | Active vulnerabilities | Ignored vulnerabilities | Secrets | Blocking |',
             '|---|---|---|---:|---:|---:|---:|']
    for r in results:
        lines.append(f'| {r["template"]} | {r["target"]} | {r["status"]} | {len(r.get("vulnerabilities", []))} | '
                     f'{len(r.get("ignored", {}).get("vulnerabilities", []))} | {len(r.get("secrets", []))} | {r.get("blocking", 0)} |')
    lines += ['', f'Scanner failures: {failed}; blocking findings: {blockers}.',
              'Verified secrets follow P2P critical-severity policy; unverified/unknown results remain visible.',
              'External Helm chart images and infrastructure provider binaries not present in built images are outside this scan.', '']
    (REPORTS / f'{name}.md').write_text('\n'.join(lines))
    print(f'Report: {REPORTS / (name + ".md")}; scanner failures={failed}, blocking={blockers}', flush=True)
    return 2 if failed else 1 if blockers else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['list', 'render', 'source', 'history', 'build', 'images', 'all'])
    parser.add_argument('--template', default=os.environ.get('SECURITY_TEMPLATE', ''))
    args = parser.parse_args()
    if THRESHOLD not in ('off', 'low', 'medium', 'high', 'critical'):
        raise ValueError('Invalid SECURITY_BLOCKING_SEVERITY')
    if PLATFORM not in ('linux/amd64', 'linux/arm64'):
        raise ValueError('SECURITY_PLATFORM must be linux/amd64 or linux/arm64')
    items = inventory(args.template)
    if args.command == 'list':
        print(json.dumps([item['template'] for item in items]))
        return 0
    STATE.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    write(REPORTS / f'{args.command}.json', {'status': 'running'})
    (REPORTS / f'{args.command}.md').write_text('Scan execution is in progress; results are incomplete.\n')
    results = []
    if args.command in ('render', 'source', 'build'):
        render(items)
    if args.command == 'source':
        results += [scan(item, 'source', STATE / 'rendered' / item['slug']) for item in items]
    if args.command in ('history', 'all'):
        item = {'template': 'repository', 'slug': 'repository', 'fingerprint': output(['git', 'rev-parse', 'HEAD'], cwd=ROOT)}
        results.append(scan(item, 'history', ROOT, history=True))
    if args.command == 'build':
        builds = build(items)
        return summary(builds, 'build')
    if args.command == 'images':
        results += images(items)
    if args.command == 'all':
        all_builds = []
        for item in items:
            render([item])
            results.append(scan(item, 'source', STATE / 'rendered' / item['slug']))
            built = build([item])
            all_builds.extend(built)
            results += images([item])
            if os.environ.get('SECURITY_KEEP_IMAGES') != 'true':
                for image in built:
                    if image['status'] == 'complete':
                        # Delete only the tag owned by this state directory; never force.
                        run(['docker', 'image', 'rm', image['tag']], stdout=subprocess.DEVNULL)
        write(STATE / 'builds.json', all_builds)
    if args.command == 'render':
        print(f'Rendered {len(items)} templates and discovered {sum(len(i["targets"]) for i in items)} images')
        return 0
    return summary(results, args.command)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Security runner failed: {type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(2)
