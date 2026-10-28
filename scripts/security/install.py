#!/usr/bin/env python3
"""Install the reviewed scanner releases, verifying committed SHA-256 digests."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / 'scripts/security/tools.json').read_text())


def install(destination):
    system = platform.system().lower()
    arch = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine())
    assets = CONFIG['assets'].get(f'{system}-{arch}')
    if not assets:
        raise RuntimeError(f'Unsupported scanner host: {system}/{platform.machine()}')
    destination.mkdir(parents=True, exist_ok=True)
    for name, asset in assets.items():
        target = destination / name
        receipt = destination / f'{name}.sha256'
        if target.is_file() and receipt.is_file():
            if hashlib.sha256(target.read_bytes()).hexdigest() == receipt.read_text().strip():
                version = subprocess.check_output([str(target), '--version'], stderr=subprocess.STDOUT, text=True)
                if CONFIG['versions'][name] in version:
                    continue
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'release.tar.gz'
            subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--silent', '--show-error', asset['url'], '--output', str(archive)], check=True)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != asset['sha256']:
                raise RuntimeError(f'{name}: release checksum mismatch')
            with tarfile.open(archive) as package:
                members = [m for m in package.getmembers() if m.name in (name, './' + name) and m.isfile()]
                if len(members) != 1:
                    raise RuntimeError(f'{name}: expected one executable in release')
                with package.extractfile(members[0]) as source, target.open('wb') as out:
                    shutil.copyfileobj(source, out)
            target.chmod(0o755)
            receipt.write_text(hashlib.sha256(target.read_bytes()).hexdigest() + '\n')
        print(f'Installed {name} {CONFIG["versions"][name]}', flush=True)


if __name__ == '__main__':
    install(Path(os.environ.get('SECURITY_TOOLS_DIR', ROOT / '.security/tools')).resolve())
