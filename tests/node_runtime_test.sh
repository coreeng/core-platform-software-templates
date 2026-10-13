#!/usr/bin/env bash
set -euo pipefail

# Exercise the copied Node binary in the actual minimal runtime stage. AMD64 Node
# needs libraries that are not required by the ARM64 binary.
platform=${TEMPLATE_TEST_PLATFORM:-linux/amd64}
context=$(mktemp -d)
images=()
cleanup() {
  rm -rf "$context"
  if [[ ${#images[@]} -gt 0 ]]; then
    docker rmi "${images[@]}" > /dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

for template in nextjs/web static/nextra; do
  dockerfile="$template/skeleton/Dockerfile"
  node_image=$(awk '$1 == "FROM" && $2 ~ /node:/ { print $2; exit }' "$dockerfile")
  {
    printf 'FROM %s AS base\n' "$node_image"
    # Keep the runtime stage and its package installs; omit application build
    # artifacts so this check exercises binary loading without a full JS build.
    awk '
      $1 == "FROM" { runtime = ($NF == "runner"); if (runtime) found = 1 }
      runtime && $1 == "COPY" && $2 == "--from=build" { next }
      runtime { print }
      END { if (!found) exit 1 }
    ' "$dockerfile"
  } > "$context/Dockerfile"
  image="template-node-runtime-$$-${template//\//-}"
  images+=("$image")
  docker build --platform "$platform" --quiet --tag "$image" "$context" > /dev/null
  docker run --rm --platform "$platform" --entrypoint node "$image" --version
  printf '%s Node runtime check passed on %s\n' "$template" "$platform"
done
