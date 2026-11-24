#!/usr/bin/env bash
set -euo pipefail

base="java/web/skeleton"
failures=0

check_file_contains() {
  local file=$1
  local pattern=$2
  local message=$3

  if ! grep -qE "$pattern" "$file"; then
    printf 'FAIL: %s: %s\n' "$file" "$message"
    failures=$((failures + 1))
  fi
}

check_file_contains "$base/.java-version" '^27$' "local Java version must match the runtime image"
check_file_contains "$base/service/build.gradle" 'sourceCompatibility = JavaVersion\.VERSION_27' "source compatibility must use Java 27"
check_file_contains "$base/service/build.gradle" 'targetCompatibility = JavaVersion\.VERSION_27' "target compatibility must use Java 27"
for dockerfile in "$base/Dockerfile" "$base"/p2p/tests/{functional,integration}/Dockerfile; do
  check_file_contains "$dockerfile" '^FROM docker.io/gradle:9\.9\.2-jdk25-resolute@sha256:[a-f0-9]{64} AS gradle-dist$' "Gradle distribution must match the wrapper"
  check_file_contains "$dockerfile" '^FROM docker.io/eclipse-temurin:27\.0\.1\.0-jdk-resolute@sha256:[a-f0-9]{64}( AS build)?$' "build and test images must run on JDK 27"
done
check_file_contains "$base/Dockerfile" 'eclipse-temurin:27\.0\.1\.0-jre-resolute' "runtime image must match .java-version"
check_file_contains "$base/gradle/wrapper/gradle-wrapper.properties" '^distributionUrl=.*\/gradle-9\.9\.2-bin\.zip$' "Gradle wrapper must use the 9.9.2 binary distribution"
check_file_contains "$base/gradle/wrapper/gradle-wrapper.properties" '^distributionSha256Sum=971fcd7150ca4ba04852c0b2ca0d2d0ab9468e14b03473eab19528809914c76b$' "Gradle distribution checksum must match Gradle 9.9.2"

for file in gradlew gradlew.bat gradle/wrapper/gradle-wrapper.jar gradle/wrapper/gradle-wrapper.properties; do
  if [[ ! -f "$base/$file" ]]; then
    printf 'FAIL: %s: missing Gradle wrapper artifact\n' "$base/$file"
    failures=$((failures + 1))
  fi
done

if [[ "$failures" -gt 0 ]]; then
  exit 1
fi

printf 'Java template checks passed\n'
