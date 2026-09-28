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

check_file_contains "$base/.java-version" '^26\.0\.2\.1$' "local Java version must match the runtime image"
check_file_contains "$base/service/build.gradle" 'sourceCompatibility = JavaVersion\.VERSION_26' "source compatibility must use Java 26"
check_file_contains "$base/service/build.gradle" 'targetCompatibility = JavaVersion\.VERSION_26' "target compatibility must use Java 26"
check_file_contains "$base/Dockerfile" 'gradle:9\.8\.0-jdk26-noble' "build image must use JDK 26"
check_file_contains "$base/Dockerfile" 'eclipse-temurin:26\.0\.2\.1_1-jre-noble' "runtime image must match .java-version"
check_file_contains "$base/gradle/wrapper/gradle-wrapper.properties" '^distributionSha256Sum=bafd5ce9cfaea0fbccfdc8439a1ac42fbd4cd9c89dc9a988228d8a2639a58e6c$' "Gradle distribution checksum must match Gradle 9.8.0"

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
