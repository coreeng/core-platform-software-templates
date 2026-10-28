#!/usr/bin/env python3
"""Run the PR's CodeQL query suites against each rendered template/module."""
import json
import os
import shutil
import subprocess
import sys

import scan


def main():
    executable = os.environ.get('CODEQL', 'codeql')
    version = scan.output([executable, 'version', '--format=json'])
    if json.loads(version)['version'] != scan.CONFIG['versions']['codeql']:
        raise RuntimeError('Install CodeQL ' + scan.CONFIG['versions']['codeql'] + ' or set CODEQL to its executable')
    items = scan.inventory(os.environ.get('SECURITY_TEMPLATE', ''))
    scan.render(items)
    if not os.environ.get('SECURITY_TEMPLATE'):
        items.append(scan.repository_snapshot())
    scan.write(scan.REPORTS / 'codeql.json', {'status': 'running'})
    results = []
    for item in items:
        workspace = scan.STATE / 'rendered' / item['slug']
        scopes = [('actions', workspace)] if (workspace / '.github/workflows').exists() else []
        for language, patterns in [('javascript-typescript', ['*.js', '*.jsx', '*.ts', '*.tsx', '*.mjs', '*.cjs', '*.mts', '*.cts']),
                                   ('python', ['*.py']), ('java-kotlin', ['*.java', '*.kt'])]:
            if any(any(workspace.rglob(pattern)) for pattern in patterns):
                scopes.append((language, workspace))
        # One database per Go module avoids autobuild selecting only one module.
        scopes += [('go', module.parent) for module in sorted(workspace.rglob('go.mod'))]
        output_dir = scan.REPORTS / item['slug'] / 'codeql'
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for language, source in scopes:
            suffix = str(source.relative_to(workspace)).replace('/', '-')
            suffix = 'root' if suffix == '.' else suffix
            name = f'{language}-{suffix}'
            database = scan.STATE / 'codeql' / item['slug'] / name
            result = scan.base_report(item, name)
            print(f'CodeQL {item["template"]} {name}', flush=True)
            try:
                database.parent.mkdir(parents=True, exist_ok=True)
                if database.exists():
                    shutil.rmtree(database)
                with (output_dir / f'{name}.log').open('w') as log:
                    scan.run([executable, 'database', 'create', database, '--source-root', source,
                              '--language', language, '--build-mode', 'autobuild' if language == 'go' else 'none',
                              '--threads', '2', '--ram', '4096'], stdout=log, stderr=subprocess.STDOUT)
                    query_language = {'java-kotlin': 'java', 'javascript-typescript': 'javascript'}.get(language, language)
                    sarif = output_dir / f'{name}.sarif'
                    scan.run([executable, 'database', 'analyze', database,
                              f'codeql/{query_language}-queries:codeql-suites/{query_language}-code-scanning.qls',
                              '--format=sarif-latest', '--output', sarif, '--threads', '2', '--ram', '4096'],
                             stdout=log, stderr=subprocess.STDOUT)
                findings = json.loads(sarif.read_text())['runs']
                result.update(status='complete', blocking=sum(len(run.get('results', [])) for run in findings))
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                result.update(status='failed', error=type(error).__name__)
            results.append(result)
    if not results:
        raise RuntimeError('No CodeQL analysis scopes discovered')
    return scan.summary(results, 'codeql')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'CodeQL setup failed: {error}', file=sys.stderr)
        sys.exit(2)
