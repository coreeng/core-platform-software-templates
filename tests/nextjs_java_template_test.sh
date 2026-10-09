#!/usr/bin/env bash
set -euo pipefail
python="${NEXTJS_JAVA_TEST_PYTHON:-python3}"
if ! "$python" -c 'import jinja2, yaml' 2>/dev/null; then
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/nextjs-java-render.XXXXXX")
  trap 'rm -rf "$tmp"' EXIT
  python3 -m venv "$tmp/venv"
  "$tmp/venv/bin/pip" -q install Jinja2==3.1.6 PyYAML==6.0.3
  python="$tmp/venv/bin/python"
fi
if [[ $# -eq 0 ]]; then
  set -- --test
fi
"$python" tests/render_nextjs_java.py "$@"
