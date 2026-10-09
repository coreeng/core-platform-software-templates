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
	@$(MAKE) test-nextjs-java-structure

## make test-nextjs-java-structure	Validate notes structure without the unpublished P2P fixture
.PHONY: test-nextjs-java-structure
test-nextjs-java-structure:
	@bash tests/nextjs_java_template_test.sh --pure-render
	@$(MAKE) test-nextjs-java-runner

## make test-nextjs-java-render		Qualify notes rendering with the local P2P fixture
.PHONY: test-nextjs-java-render
test-nextjs-java-render:
	@bash tests/nextjs_java_template_test.sh
	@$(MAKE) test-nextjs-java-runner

## make test-nextjs-java-runner		Test disposable notes runner failure and cleanup contracts
.PHONY: test-nextjs-java-runner
test-nextjs-java-runner:
	@test -f tests/nextjs_java_runner_test.py || { echo "Missing notes runner contract tests" >&2; exit 1; }
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'nextjs_java_runner_test.py'

## make test-nextjs-java-build		Build notes application and test images with Docker
.PHONY: test-nextjs-java-build
test-nextjs-java-build:
	@python3 tests/nextjs_java_local.py build

## make test-nextjs-java-functional	Run owned disposable notes database/browser tests
.PHONY: test-nextjs-java-functional
test-nextjs-java-functional:
	@python3 tests/nextjs_java_local.py functional
