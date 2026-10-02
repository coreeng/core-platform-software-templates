#!/usr/bin/env bash
set -euo pipefail

app_templates=(
  "docker/web"
  "go/web"
  "java/web"
  "nextjs/web"
  "python/web"
  "static/nextra"
)

failures=0

for template in "${app_templates[@]}"; do
  template_file="$template/template.yaml"
  common_values="$template/skeleton/p2p/config/common.yaml"
  makefile="$template/skeleton/Makefile"
  test_directory="$template/skeleton/p2p/tests"

  if ! awk '
    $0 == "  ingress:" {
      getline
      if ($0 == "    enabled: false") found = 1
    }
    END { exit(found ? 0 : 1) }
  ' "$template_file"; then
    printf 'FAIL: %s: config.ingress.enabled must default to false\n' "$template_file"
    failures=$((failures + 1))
  fi

  if ! awk '
    $0 == "ingress:" {
      getline
      if ($0 == "  enabled: ${p2p_app_config_ingress_enabled}") found = 1
    }
    END { exit(found ? 0 : 1) }
  ' "$common_values"; then
    printf 'FAIL: %s: ingress.enabled must use the app.yaml config value\n' "$common_values"
    failures=$((failures + 1))
  fi

  if ! grep -R -q 'SERVICE_ENDPOINT' "$test_directory"; then
    printf 'FAIL: %s: tests must target the in-cluster service\n' "$test_directory"
    failures=$((failures + 1))
  fi

  case "$template" in
    docker/web|go/web)
      if ! grep -R -q 'INGRESS_ENDPOINT' "$test_directory" || ! grep -R -q 'godog.ErrSkip' "$test_directory"; then
        printf 'FAIL: %s: ingress scenarios must skip when ingress is disabled\n' "$test_directory"
        failures=$((failures + 1))
      fi
      ;;
    python/web)
      if ! grep -R -q 'INGRESS_ENDPOINT' "$test_directory" || ! grep -R -q 'scenario.skip("Ingress is disabled")' "$test_directory"; then
        printf 'FAIL: %s: ingress scenarios must skip when ingress is disabled\n' "$test_directory"
        failures=$((failures + 1))
      fi
      ;;
  esac

  if ! grep -qF '    endpoint: service' "$common_values" ||
     ! grep -A2 '^tests:' "$common_values" | grep -qF '    enabled: false'; then
    printf 'FAIL: %s: automated tests must use Service routing\n' "$common_values"
    failures=$((failures + 1))
  fi
done

if [[ "$failures" -gt 0 ]]; then
  exit 1
fi

printf 'Application ingress checks passed\n'
