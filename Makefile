# use bash for advanced variable substitutions
SHELL := /bin/bash

# use local yamale & yamllint if present, otherwise fallback to docker
YAMALE := $$(which yamale 2>/dev/null || echo docker run --rm -v "$${PWD}":/templates -w /templates quay.io/helmpack/chart-testing yamale)
YAMLLINT := $$(which yamllint 2>/dev/null || echo docker run --rm --mount type=bind,source=.,target=/data docker.io/cytopia/yamllint -s)

.PHONY: default
default: help

.PHONY: help
help: Makefile
	@echo "Usage: "
	@sed -n 's/^## /   /p' Makefile

## make templates-validate			Validate template definitions
.PHONY: templates-validate
templates-validate:
	@ERRVAL=0 ; \
	set -o pipefail ; \
	name_array=() ; \
	for ENV_YAML in $$(find . -not -path './.git/*' -maxdepth 3 -iname 'template.yaml' | sed -e "s@./@@" | sort) ; do \
		FILENAME=$$(basename $$ENV_YAML) ; \
		DIRNAME=$$(dirname $$ENV_YAML) ; \
		$(YAMALE) "$${ENV_YAML}" | sed -e "s@$(PWD)/@@g" -e "/Validation /d" ; \
		ERRVAL=$$(($${ERRVAL} + $$?)) ; \
		$(YAMLLINT) "$${ENV_YAML}" ; \
		ERRVAL=$$(($${ERRVAL} + $$?)) ; \
	done ; \
	if [ "$${ERRVAL}" != 0 ] ; then \
		echo "Template validation tests failed" ; \
	else \
		echo "Template validation tests passed" ; \
	fi ; \
	exit "$${ERRVAL}"
	@bash tests/template_docs_test.sh
	@bash tests/app_ingress_test.sh
	@bash tests/dockerfile_user_test.sh
	@bash tests/security_ignore_test.sh
	@bash tests/java_template_test.sh
	@bash tests/nextjs_template_test.sh
	@bash tests/node_runtime_test.sh

SECURITY_DIR ?= $(CURDIR)/.security
SECURITY_TOOLS_DIR ?= $(SECURITY_DIR)/tools
SECURITY_PYTHON := $(SECURITY_DIR)/venv/bin/python
export SECURITY_DIR SECURITY_TOOLS_DIR SECURITY_TEMPLATE SECURITY_PLATFORM SECURITY_BLOCKING_SEVERITY SECURITY_BASE

## make security-setup                     Install pinned rendering dependencies
.PHONY: security-setup
security-setup:
	python3 -m venv "$(SECURITY_DIR)/venv"
	"$(SECURITY_PYTHON)" -m pip install -r scripts/security/requirements.txt

## make security-tools                     Install checksum-verified Trivy and TruffleHog
.PHONY: security-tools
security-tools:
	python3 scripts/security/install.py

## make security-list                      List templates for CI matrix generation
.PHONY: security-list
security-list:
	@python3 scripts/security/scan.py list

## make security-render                    Render isolated template copies
## make security-source                    Scan rendered dependencies, licenses and secrets
## make security-history                   Scan repository Git history for secrets
## make security-build                     Build every template image using its Make targets
## make security-images                    Scan images from the recorded build manifest
## make security-all                       Render, scan source/history, build and scan images
.PHONY: security-render security-source security-history security-build security-images security-all
security-render security-source security-history security-build security-images security-all:
	"$(SECURITY_PYTHON)" scripts/security/scan.py $(@:security-%=%)

## make security-test                      Test scan coverage, policy and failure handling
.PHONY: security-test
security-test:
	"$(SECURITY_PYTHON)" -m unittest discover -s tests/security -p 'test_*.py'
	node --test tests/security/*.test.cjs

## make security-codeql                    Run pinned CodeQL CLI on rendered templates/modules
.PHONY: security-codeql
security-codeql:
	"$(SECURITY_PYTHON)" scripts/security/codeql.py
