# use bash for advanced variable substitutions
SHELL := /bin/bash

# Use local Yamale when available, with Docker as a fallback.
YAMALE := $$(which yamale 2>/dev/null || echo docker run --rm -v "$${PWD}":/templates -w /templates quay.io/helmpack/chart-testing yamale)

# The image contains yamllint 1.38.0.
YAMLLINT_IMAGE := docker.io/pipelinecomponents/yamllint:0.35.27@sha256:f7f7b4f8824839e33690a880dbe20944128b0dc9c55522a0b92a29b3a905cecf
YAMLLINT := docker run --rm --mount "type=bind,source=$(CURDIR),target=/data,readonly" --workdir /data --entrypoint yamllint $(YAMLLINT_IMAGE) -s

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
	@bash tests/showcase_test.sh
	@bash tests/dockerfile_user_test.sh
	@bash tests/security_ignore_test.sh
	@bash tests/java_template_test.sh
	@bash tests/nextjs_template_test.sh
	@bash tests/node_runtime_test.sh
