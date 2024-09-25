#!/bin/bash
set -euo pipefail

subenv=$1
tenant_name=$2
app_name=${3:-$tenant_name}
scale_down=${4:-false}
timeout=${5:-"15m"}

POD_NAME=${app_name}-${subenv}-test

./helm-test.sh executeTests $subenv $tenant_name $app_name false $timeout $tenant_name-$subenv-test

./helm-test.sh executeTests $subenv $tenant_name $app_name $scale_down $timeout $tenant_name-$subenv-test-validate

