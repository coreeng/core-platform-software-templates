#!/usr/bin/env bash
set -euo pipefail
root="$(pwd)"
work="$(mktemp -d "${TMPDIR:-/tmp}/template-ingress.XXXXXX")"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
cat > "$work/include.mk" <<'EOF'
SHELL := /bin/bash
export p2p_app_config_ingress_enabled
EOF
cat > "$work/bin/curl" <<'EOF'
#!/usr/bin/env bash
cp "$FAKE_INCLUDE" .p2p.mk
EOF
cat > "$work/bin/helm" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$CAPTURE"
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
  for mode in LOCAL_HTTP EXISTING_INGRESS DISABLED LEGACY; do
    context=core-platform/engineering domain=trial.localhost class=traefik enabled=true endpoint=service tests=false
    case "$mode" in
      EXISTING_INGRESS) domain=apps.example.com class=nginx endpoint=ingress tests=true ;;
      DISABLED) enabled=false domain= class= tests=true ;;
      LEGACY) context= domain=legacy.example.com endpoint=ingress tests=true ;;
    esac
    CORECTL_CONTEXT="$context" P2P_INGRESS_MODE="$mode" P2P_INGRESS_ENABLED="$enabled" \
      P2P_INGRESS_DOMAIN="$domain" P2P_INGRESS_CLASS="$class" BASE_DOMAIN=legacy.example.com \
      make -s -C "$directory" deploy-functional p2p_app_name=shop p2p_namespace=shop-functional \
        p2p_app_config_ingress_enabled=true > /dev/null
    grep -qx '0.17.0' "$CAPTURE"
    grep -qx "ingress.domain=$domain" "$CAPTURE"
    grep -qx "tests.nft.endpoint=$endpoint" "$CAPTURE"
    if [[ "$mode" != LEGACY ]]; then
      grep -qx "ingress.className=$class" "$CAPTURE"
      grep -qx "tests.ingress.enabled=$tests" "$CAPTURE"
    fi
  done
  for assignment in P2P_INGRESS_DOMAIN=other.example P2P_INGRESS_ENABLED=false P2P_INGRESS_CLASS=nginx P2P_INGRESS_MODE=EXISTING_INGRESS; do
    for channel in command flags; do
      arguments=(); flags=
      if [[ "$channel" == command ]]; then arguments+=("$assignment"); else flags="$assignment"; fi
      if CORECTL_CONTEXT=core-platform/engineering P2P_INGRESS_MODE=LOCAL_HTTP P2P_INGRESS_ENABLED=true \
        P2P_INGRESS_DOMAIN=trial.localhost P2P_INGRESS_CLASS=traefik MAKEFLAGS="$flags" \
        make -s -C "$directory" deploy-functional "${arguments[@]}" >/dev/null 2>&1; then
        echo "FAIL: $template accepted $channel override $assignment" >&2; exit 1
      fi
    done
  done
  CORECTL_CONTEXT=core-platform/engineering P2P_INGRESS_MODE=LOCAL_HTTP P2P_INGRESS_ENABLED=true \
    P2P_INGRESS_DOMAIN=trial.localhost P2P_INGRESS_CLASS=traefik GNUMAKEFLAGS=-e \
    p2p_ingress_args=ignored p2p_nft_endpoint=ingress \
    make -s -C "$directory" deploy-functional p2p_app_name=shop p2p_namespace=shop-functional \
      p2p_ingress_args=ignored p2p_nft_endpoint=ingress >/dev/null
  grep -qx 'tests.nft.endpoint=service' "$CAPTURE"
  grep -qx 'tests.ingress.enabled=false' "$CAPTURE"
  grep -qx 'ingress.className=traefik' "$CAPTURE"
  if CORECTL_CONTEXT=core-platform/engineering P2P_INGRESS_MODE= make -s -C "$directory" deploy-functional >/dev/null 2>&1; then
    echo "FAIL: $template accepted unresolved native ingress" >&2; exit 1
  fi
done
printf 'Native local/HTTPS/disabled/legacy Make contracts passed for six templates\n'
