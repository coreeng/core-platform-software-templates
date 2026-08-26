ARG OPENTOFU_VERSION=1.12.5
ARG TERRAGRUNT_VERSION=1.1.1
ARG CLOUD_SQL_PROXY_VERSION=2.24.1
ARG YQ_VERSION=4.53.3
ARG JQ_VERSION=1.8.1
ARG GCLOUD_CLI_VERSION=576.0.0
ARG CLOUD_SQL_PROXY_SHA256_AMD64=fae2766aac9d614a2bdef2f2a7778f3d054f3acd5ff07a81a9e300bd471512eb
ARG CLOUD_SQL_PROXY_SHA256_ARM64=da49fd73b0d33c0ab8e5dfc19dfb104cdd969ebd355eef8fd3b079c20a723c82

FROM docker.io/debian:trixie AS tooling

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /tmp

ARG OPENTOFU_VERSION
ARG TERRAGRUNT_VERSION
ARG CLOUD_SQL_PROXY_VERSION
ARG YQ_VERSION
ARG JQ_VERSION
ARG GCLOUD_CLI_VERSION
ARG CLOUD_SQL_PROXY_SHA256_AMD64
ARG CLOUD_SQL_PROXY_SHA256_ARM64
ARG TARGETARCH

RUN case "$TARGETARCH" in \
   amd64|arm64) ;; \
   *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
  esac

# Install dependencies
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt \
 apt-get update \
 && apt-get install --no-install-recommends -y \
  ca-certificates \
  curl \
  git \
  gnupg \
  make \
  postgresql-client \
  vim-tiny \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /usr/share/doc/* \
 && rm -f /var/lib/dpkg/info/*.md5sums

# Install gcloud CLI
VOLUME ["/root/.config/gcloud"]
RUN --mount=type=cache,target=/var/cache/apt \
 echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
 && curl -Ls https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
 && apt-get update \
 && apt-get install --no-install-recommends -y \
  google-cloud-cli=${GCLOUD_CLI_VERSION}-0 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && gcloud config set core/disable_usage_reporting true \
 && gcloud config set component_manager/disable_update_check true \
 && gcloud config set metrics/environment github_docker_image \
 && gcloud --version \
 && find /usr/lib/google-cloud-sdk -type d \( -name test -o -name tests -o -name testdata -o -name test_data -o -name __pycache__ \) -prune -exec rm -rf {} + \
 && find /usr/lib/google-cloud-sdk -type d \( -name docs -o -name doc \) -prune -exec rm -rf {} + \
 && find /usr/lib/google-cloud-sdk -type d -name dummyserver -prune -exec rm -rf {} + \
 && find /usr/lib/google-cloud-sdk -name '*.pyc' -delete \
 && rm -rf /usr/share/doc/* /root/.cache/pip \
 && rm -f /var/lib/dpkg/info/*.md5sums

# Install jq
RUN jq_asset="jq-linux-${TARGETARCH}" \
 && curl -Lsfo "$jq_asset" "https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/${jq_asset}" \
 && curl -Lsfo jq-sha256sum.txt "https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/sha256sum.txt" \
 && awk -v asset="$jq_asset" '$2 == asset { print }' jq-sha256sum.txt | sha256sum -c - \
 && install -o root -g root -m 0755 "$jq_asset" /usr/local/bin/jq \
 && rm "$jq_asset" jq-sha256sum.txt \
 && jq --version

# Install cloud-sql-proxy
RUN case "$TARGETARCH" in \
   amd64) cloud_sql_proxy_sha256="$CLOUD_SQL_PROXY_SHA256_AMD64" ;; \
   arm64) cloud_sql_proxy_sha256="$CLOUD_SQL_PROXY_SHA256_ARM64" ;; \
   *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
  esac \
 && curl -Lsfo cloud-sql-proxy "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v${CLOUD_SQL_PROXY_VERSION}/cloud-sql-proxy.linux.${TARGETARCH}" \
 && printf '%s  %s\n' "$cloud_sql_proxy_sha256" cloud-sql-proxy | sha256sum -c - \
 && install -o root -g root -m 0755 cloud-sql-proxy /usr/local/bin/cloud-sql-proxy \
 && rm cloud-sql-proxy \
 && cloud-sql-proxy --version

# Install opentofu
RUN opentofu_asset="tofu_${OPENTOFU_VERSION}_linux_${TARGETARCH}.tar.gz" \
 && curl -Lsfo opentofu.tgz "https://github.com/opentofu/opentofu/releases/download/v${OPENTOFU_VERSION}/${opentofu_asset}" \
 && curl -Lsfo opentofu-sha256sums "https://github.com/opentofu/opentofu/releases/download/v${OPENTOFU_VERSION}/tofu_${OPENTOFU_VERSION}_SHA256SUMS" \
 && awk -v asset="$opentofu_asset" '$2 == asset { print $1 "  opentofu.tgz" }' opentofu-sha256sums | sha256sum -c - \
 && tar zxf opentofu.tgz tofu \
 && install -o root -g root -m 0755 tofu /usr/local/bin/ \
 && rm opentofu.tgz opentofu-sha256sums tofu \
 && tofu version

# Install terragrunt
RUN terragrunt_asset="terragrunt_linux_${TARGETARCH}" \
 && curl -Lsfo terragrunt "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/${terragrunt_asset}" \
 && curl -Lsfo terragrunt-sha256sums "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/SHA256SUMS" \
 && awk -v asset="$terragrunt_asset" '$2 == asset { print $1 "  terragrunt" }' terragrunt-sha256sums | sha256sum -c - \
 && install -o root -g root -m 0755 terragrunt /usr/local/bin/ \
 && rm terragrunt terragrunt-sha256sums \
 && terragrunt -version

# Install yq
RUN yq_asset="yq_linux_${TARGETARCH}" \
 && curl -Lsfo "$yq_asset" "https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/${yq_asset}" \
 && curl -Lsfo yq-checksums "https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/checksums" \
 && checksum_line="$(grep -E "^${yq_asset}[[:space:]]" yq-checksums)" \
 && yq_sha256="$(printf '%s\n' "$checksum_line" | tr -s '[:space:]' ' ' | cut -d ' ' -f 19)" \
 && test -n "$yq_sha256" \
 && printf '%s  %s\n' "$yq_sha256" "$yq_asset" | sha256sum -c - \
 && install -o root -g root -m 0755 "$yq_asset" /usr/local/bin/yq \
 && rm "$yq_asset" yq-checksums \
 && yq --version

FROM tooling AS lint

WORKDIR /app

# Copy infrastructure
COPY infrastructure/ ./

# Check OpenTofu formatting and Terragrunt formatting and semantics
RUN tofu fmt -check -diff -recursive \
 && terragrunt hcl fmt --check \
 && P2P_VERSION=lint environment=lint tenant_name=lint app_name=lint terragrunt hcl validate --working-dir=code

# Initialize locally and run credential-free infrastructure tests
RUN tofu -chdir=code init -backend=false && tofu -chdir=code test

FROM lint

# Cache terraform providers, and persist cache in the image
RUN --mount=type=cache,target=/var/tmp/terraform \
 TF_PLUGIN_CACHE_DIR=/var/tmp/terraform \
 TF_PLUGIN_CACHE_DESTINATION=/var/cache/terraform \
 make infra-init-cache
ENV TF_PLUGIN_CACHE_DIR=/var/cache/terraform

ENV CHECKPOINT_DISABLE=true

# Set version
ARG P2P_VERSION
ENV P2P_VERSION=${P2P_VERSION}
