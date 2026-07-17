#!/usr/bin/env bash
set -euo pipefail

package_file="nextjs/web/skeleton/package.json"
lock_file="nextjs/web/skeleton/yarn.lock"
failures=0

if ! grep -qE '^  "name": "app",$' "$package_file"; then
  printf 'FAIL: %s: Next.js must use the stable package name "app"\n' "$package_file"
  failures=$((failures + 1))
fi

if grep -q '{{ name }}' "$package_file" "$lock_file"; then
  printf 'FAIL: Next.js package and lockfile names must not be rendered from {{ name }}\n'
  failures=$((failures + 1))
fi

if ! grep -qE '^"app@workspace:\.":$' "$lock_file"; then
  printf 'FAIL: %s: missing app@workspace:. entry\n' "$lock_file"
  failures=$((failures + 1))
fi

for template in nextjs/web static/nextra; do
  package_file="$template/skeleton/package.json"
  eslint_file="$template/skeleton/eslint.config.mjs"
  makefile="$template/skeleton/Makefile"

  if ! grep -qF '"lint": "eslint .",' "$package_file"; then
    printf 'FAIL: %s: lint script must use the ESLint CLI\n' "$package_file"
    failures=$((failures + 1))
  fi
  if grep -q '@eslint/eslintrc' "$package_file" "$eslint_file"; then
    printf 'FAIL: %s: native flat config must not use @eslint/eslintrc\n' "$template"
    failures=$((failures + 1))
  fi
  if ! grep -q 'eslint-config-next/core-web-vitals' "$eslint_file"; then
    printf 'FAIL: %s: missing native Next.js flat config\n' "$eslint_file"
    failures=$((failures + 1))
  fi
  if ! grep -q 'yarn lint' "$makefile"; then
    printf 'FAIL: %s: lint-app must run the application linter\n' "$makefile"
    failures=$((failures + 1))
  fi
done

if ! grep -q 'node:26.5.0-bookworm-slim AS node-runtime' \
  static/nextra/skeleton/p2p/tests/functional/Dockerfile; then
  printf 'FAIL: static Nextra functional tests must use the Node 26 runtime\n'
  failures=$((failures + 1))
fi

if [[ "$failures" -gt 0 ]]; then
  exit 1
fi

printf 'Next.js template checks passed\n'
