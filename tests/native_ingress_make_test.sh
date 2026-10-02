#!/usr/bin/env bash
set -euo pipefail
work="$(mktemp -d "${TMPDIR:-/tmp}/template-ingress.XXXXXX")"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
cat > "$work/include.mk" <<'EOF'
SHELL := /bin/bash
override p2p_deployment_values := .p2p-deployment-values.yaml
.PHONY: p2p-prepare-deployment-values
p2p-prepare-deployment-values:
	rm -f .p2p-deployment-values.yaml
	test "$${FAIL_PREPARATION:-false}" = false
	printf '%s\n' '{"ingress":{"enabled":true,"domain":"trial.localhost","className":"traefik"},"tests":{"ingress":{"enabled":false},"nft":{"endpoint":"service"}}}' > .p2p-deployment-values.yaml
EOF
cat > "$work/bin/curl" <<'EOF'
#!/usr/bin/env bash
cp "$FAKE_INCLUDE" .p2p.mk
EOF
cat > "$work/bin/helm" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$CAPTURE"
if [[ "$1" == upgrade ]]; then test -f .p2p-deployment-values.yaml; fi
EOF
cat > "$work/bin/envsubst" <<'EOF'
#!/usr/bin/env bash
cat
EOF
chmod +x "$work/bin/"*
export PATH="$work/bin:$PATH" FAKE_INCLUDE="$work/include.mk" CAPTURE="$work/args"
for template in docker/web go/web java/web nextjs/web python/web static/nextra; do
  directory="$work/${template//\//-}"
  mkdir -p "$directory/p2p"
  cp "$template/skeleton/Makefile" "$directory/Makefile"
  cp -r "$template/skeleton/p2p/config" "$directory/p2p/config"
  make -s -C "$directory" p2p-deployment-values-contract
  for stage in functional nft integration extended-test prod; do
    make -s -C "$directory" "deploy-$stage" p2p_app_name=shop p2p_namespace="shop-$stage" \
      p2p_deployment_values=other.yaml >/dev/null
    grep -qx '0.17.0' "$CAPTURE"
    python3 - "$CAPTURE" <<'PY'
import sys
from pathlib import Path
args = Path(sys.argv[1]).read_text().splitlines()
assert args[-3:] == ['-f', '.p2p-deployment-values.yaml', '--atomic'], args
assert not any(arg.startswith(('tests.nft.endpoint=', 'ingress.domain=', 'tests.ingress.enabled=')) for arg in args)
PY
  done
  rm -f "$CAPTURE"
  if FAIL_PREPARATION=true make -s -C "$directory" deploy-functional >/dev/null 2>&1; then
    echo "FAIL: $template deployed after failed preparation" >&2; exit 1
  fi
  test ! -e "$CAPTURE"
  test ! -e "$directory/.p2p-deployment-values.yaml"
  if grep -qE 'P2P_INGRESS|p2p_ingress_args|p2p_nft_endpoint|BASE_DOMAIN' "$directory/Makefile"; then
    echo "FAIL: $template contains ingress-specific Make logic" >&2; exit 1
  fi
done
printf 'Shared deployment-values Make contracts passed for six templates and five stages\n'
