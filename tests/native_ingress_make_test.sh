#!/usr/bin/env bash
set -euo pipefail
work="$(mktemp -d "${TMPDIR:-/tmp}/template-ingress.XXXXXX")"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
cat > "$work/include.mk" <<'EOF'
SHELL := /bin/bash
export p2p_app_config_ingress_enabled := $(shell yq -r '.config.ingress.enabled' app.yaml)
EOF
cat > "$work/bin/curl" <<'EOF'
#!/usr/bin/env bash
cp "$FAKE_INCLUDE" .p2p.mk
EOF
cat > "$work/bin/helm" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" > "$CAPTURE"
if [[ "$1" == upgrade ]]; then
  while (( $# )); do
    if [[ "$1" == -f ]]; then cat "$2" > "$CAPTURE_VALUES"; break; fi
    shift
  done
fi
EOF
chmod +x "$work/bin/"*
export PATH="$work/bin:$PATH" FAKE_INCLUDE="$work/include.mk" CAPTURE="$work/args" CAPTURE_VALUES="$work/values"
for template in docker/web go/web java/web nextjs/web python/web static/nextra; do
  directory="$work/${template//\//-}"
  mkdir -p "$directory/p2p"
  cp "$template/skeleton/Makefile" "$directory/Makefile"
  cp -r "$template/skeleton/p2p/config" "$directory/p2p/config"
  for mode in LOCAL_HTTP EXISTING_INGRESS DISABLED LEGACY; do
    domain=trial.localhost class=traefik enabled=true
    case "$mode" in
      EXISTING_INGRESS) domain=apps.example.com class=nginx ;;
      DISABLED) enabled=false domain= class= ;;
      LEGACY) domain=legacy.example.com class= ;;
    esac
    printf 'config:\n  ingress:\n    enabled: %s\n' "$enabled" > "$directory/app.yaml"
    for stage in functional nft integration extended-test prod; do
      P2P_INGRESS_ENABLED="$(if [[ "$enabled" == true ]]; then echo false; else echo true; fi)" \
        P2P_INGRESS_DOMAIN="$domain" P2P_INGRESS_CLASS="$class" \
        make -s -C "$directory" "deploy-$stage" p2p_app_name=shop p2p_namespace="shop-$stage" >/dev/null
      grep -qx '0.17.0' "$CAPTURE"
      grep -qx "  enabled: $enabled" "$CAPTURE_VALUES"
      grep -qx "  domain: \"$domain\"" "$CAPTURE_VALUES"
      grep -qx "  className: \"$class\"" "$CAPTURE_VALUES"
      grep -qx '    endpoint: service' "$CAPTURE_VALUES"
      grep -A2 '^tests:' "$CAPTURE_VALUES" | grep -qx '    enabled: false'
    done
  done
  if grep -qE 'P2P_INGRESS|p2p_ingress_args|p2p_nft_endpoint|BASE_DOMAIN|deployment-values|corectl' "$directory/Makefile"; then
    echo "FAIL: $template contains ingress-specific Make logic or preparation coupling" >&2; exit 1
  fi
done
printf 'P2P environment Make contracts passed for six templates, five stages and four modes\n'
