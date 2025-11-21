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
