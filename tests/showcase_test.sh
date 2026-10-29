#!/usr/bin/env bash
set -euo pipefail
for template in docker/web go/web java/web nextjs/web python/web static/nextra; do
  root="$template/skeleton"
  workflow="$root/.github/workflows/fast-feedback.yaml"
  grep -qF '      showcase:' "$workflow"
  grep -A5 '      showcase:' "$workflow" | grep -qF 'default: false'
  # Only an explicitly flagged dispatch can enable the reusable job.
  grep -qF "github.event_name == 'workflow_dispatch' && inputs.showcase" "$workflow"
  grep -Eq '^p2p-showcase:[[:space:]]+deploy-showcase$' "$root/Makefile"
  test -f "$root/p2p/config/showcase.yaml"
  grep -qF 'Showcase' "$root/AGENTS.md"
done
printf 'Showcase template contracts passed\n'
