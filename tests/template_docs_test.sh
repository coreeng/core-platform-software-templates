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

check_file_contains() {
  local file=$1
  local pattern=$2
  local message=$3

  if ! grep -qE "$pattern" "$file"; then
    printf 'FAIL: %s: %s\n' "$file" "$message"
    failures=$((failures + 1))
  fi
}

check_file_not_contains() {
  local file=$1
  local pattern=$2
  local message=$3

  if grep -qE "$pattern" "$file"; then
    printf 'FAIL: %s: %s\n' "$file" "$message"
    failures=$((failures + 1))
  fi
}

for template in "${app_templates[@]}"; do
  agents_file="$template/skeleton/AGENTS.md"
  readme_file="$template/skeleton/README.md"

  if [[ ! -f "$agents_file" ]]; then
    printf 'FAIL: %s missing generated AGENTS.md\n' "$template"
    failures=$((failures + 1))
    continue
  fi

  check_file_contains "$agents_file" '^## Template And Tech Stack$' "missing template/tech stack section"
  check_file_contains "$agents_file" '^## Core Platform P2P$' "missing standard P2P section"
  check_file_contains "$agents_file" 'fast-feedback.yaml' "must document fast feedback workflow"
  check_file_contains "$agents_file" 'p2p/config/common.yaml' "must document common config"
  check_file_contains "$agents_file" 'p2p/config/functional.yaml' "must document functional config"
  check_file_contains "$agents_file" 'Functional tests' "must document functional tests"
  check_file_contains "$agents_file" 'Non-functional tests' "must document NFT tests"
  check_file_contains "$agents_file" 'Integration tests' "must document integration tests"
  check_file_contains "$agents_file" 'Extended tests' "must document extended tests"
  check_file_not_contains "$agents_file" 'local P2P|run the P2P locally|Executing P2P targets Locally|corectl' "must not document local P2P execution"

  check_file_not_contains "$readme_file" 'Path to Production|P2P Overview|Core Platform P2P|Functional Testing|Non-Functional Testing|Integration Testing|Extended Testing|## NFT|## Extended test' "README should not explain P2P/test stages"
done

monitoring_agents="monitoring-stack/skeleton/AGENTS.md"
monitoring_readme="monitoring-stack/skeleton/README.md"

if [[ ! -f "$monitoring_agents" ]]; then
  printf 'FAIL: monitoring-stack missing generated AGENTS.md\n'
  failures=$((failures + 1))
else
  check_file_contains "$monitoring_agents" '^## Template And Tech Stack$' "missing monitoring template/tech stack section"
  check_file_contains "$monitoring_agents" '^## Core Platform P2P$' "missing monitoring P2P section"
  check_file_contains "$monitoring_agents" 'integration.yaml' "must document integration config"
  check_file_contains "$monitoring_agents" 'prod.yaml' "must document prod config"
  check_file_not_contains "$monitoring_agents" 'Functional tests|Non-functional tests|Extended tests|local P2P|corectl' "monitoring AGENTS should stay monitoring-specific"
fi

check_file_contains "$monitoring_readme" 'p2p/config/integration.yaml' "README should document integration monitored delivery units"
check_file_contains "$monitoring_readme" 'p2p/config/prod.yaml' "README should document prod monitored delivery units"
check_file_not_contains "$monitoring_readme" 'Functional Testing|Non-Functional Testing|Extended Testing|## NFT|local P2P|corectl' "monitoring README should not contain app P2P guidance"

if [[ "$failures" -gt 0 ]]; then
  exit 1
fi

printf 'Template documentation checks passed\n'
