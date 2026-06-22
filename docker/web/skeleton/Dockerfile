FROM docker.io/stefanprodan/podinfo:6.14.0

USER root

# hadolint ignore=DL3018
RUN apk upgrade --no-cache libcrypto3 libssl3

USER app

EXPOSE 9898
