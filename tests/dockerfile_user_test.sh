#!/usr/bin/env bash
set -euo pipefail

failures=0

while IFS=: read -r file line instruction; do
  user=$(awk '{ print $2 }' <<< "$instruction")
  if [[ "$user" =~ ^[0-9]+(:[0-9]+)?$ ]]; then
    continue
  fi

  printf 'FAIL: %s:%s: USER must use a numeric UID to satisfy Hadolint DL3066\n' \
    "$file" "$line"
  failures=$((failures + 1))
done < <(grep -RInE '^[[:space:]]*USER[[:space:]]+' \
  --include=Dockerfile \
  --exclude-dir=.git \
  --exclude-dir=.worktrees \
  . || true)

if [[ "$failures" -gt 0 ]]; then
  exit 1
fi

printf 'Dockerfile USER checks passed\n'
