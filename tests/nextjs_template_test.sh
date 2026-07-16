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

if [[ "$failures" -gt 0 ]]; then
  exit 1
fi

printf 'Next.js template checks passed\n'
