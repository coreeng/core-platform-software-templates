# Independent proof slice: unreleased portability helper must be supplied locally.
P2P_TENANT_NAME ?= {{ tenant }}
P2P_APP_NAME ?= {{ name }}
ifeq ($(strip $(P2P_HELPER_DIR)),)
$(error P2P_HELPER_DIR must point to the reviewed local Task8 fixture)
endif
ifeq ($(wildcard $(P2P_HELPER_DIR)/scripts/build-image.sh),)
$(error P2P_HELPER_DIR does not contain scripts/build-image.sh)
endif
include $(P2P_HELPER_DIR)/p2p.mk
include $(P2P_HELPER_DIR)/p2p-build.mk
P2P_IMAGE_NAMES := $(P2P_APP_NAME)-frontend $(P2P_APP_NAME)-backend
.NOTPARALLEL:
.PHONY: build-app push-app p2p-build p2p-functional p2p-integration p2p-extended-test p2p-prod
p2p-build: build-app push-app
p2p-functional: build-functional push-functional deploy-functional run-functional
p2p-integration: build-integration push-integration deploy-integration run-integration
p2p-extended-test: build-extended-test push-extended-test deploy-extended-test run-extended-test
p2p-prod: deploy-prod
build-app:
	mkdir -p .p2p
	$(call p2p-build-image,frontend,frontend/Dockerfile,$(P2P_REGISTRY_FAST_FEEDBACK)/$(P2P_APP_NAME)-frontend:$(P2P_VERSION),.p2p/frontend.digest)
	$(call p2p-build-image,backend,backend/Dockerfile,$(P2P_REGISTRY_FAST_FEEDBACK)/$(P2P_APP_NAME)-backend:$(P2P_VERSION),.p2p/backend.digest)
push-app:
	docker image push "$(P2P_REGISTRY_FAST_FEEDBACK)/$(P2P_APP_NAME)-frontend:$(P2P_VERSION)"
	docker image push "$(P2P_REGISTRY_FAST_FEEDBACK)/$(P2P_APP_NAME)-backend:$(P2P_VERSION)"
build-functional build-integration build-extended-test:
	mkdir -p .p2p
	$(call p2p-build-image,p2p/tests,p2p/tests/Dockerfile,$(p2p_image_tag),.p2p/test.digest)
push-functional push-integration push-extended-test:
	docker image push "$(p2p_image_tag)"
deploy-%:
	test -n "$(p2p_namespace)"
	helm upgrade --install "$(P2P_APP_NAME)" p2p/chart --namespace "$(p2p_namespace)" \
	  -f p2p/config/$*.yaml \
	  --set-string frontend.image.repository="$(p2p_registry)/$(P2P_APP_NAME)-frontend" \
	  --set-string backend.image.repository="$(p2p_registry)/$(P2P_APP_NAME)-backend" \
	  --set-string frontend.image.tag="$(P2P_VERSION)" --set-string backend.image.tag="$(P2P_VERSION)" \
	  --set-string tests.image.repository="$(p2p_registry)/$(P2P_APP_NAME)-$(if $(filter extended-test,$*),extended,$*)" \
	  --set-string tests.image.tag="$(P2P_VERSION)" --atomic --wait --timeout 10m
run-functional run-integration run-extended-test:
	helm test "$(P2P_APP_NAME)" --namespace "$(p2p_namespace)" --logs --timeout 5m
p2p-nft:
	$(error NFT is unsupported by this proof template)
