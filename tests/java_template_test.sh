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

check_file_contains "$base/.java-version" '^26\.0\.1$' "local Java version must match the runtime image"
check_file_contains "$base/service/build.gradle" 'sourceCompatibility = JavaVersion\.VERSION_26' "source compatibility must use Java 26"
check_file_contains "$base/service/build.gradle" 'targetCompatibility = JavaVersion\.VERSION_26' "target compatibility must use Java 26"
check_file_contains "$base/Dockerfile" 'gradle:9\.6\.1-jdk26-noble' "build image must use JDK 26"
check_file_contains "$base/Dockerfile" 'eclipse-temurin:26\.0\.1_8-jre-noble' "runtime image must match .java-version"
check_file_contains "$base/gradle/wrapper/gradle-wrapper.properties" '^distributionSha256Sum=9c0f7faeeb306cb14e4279a3e084ca6b596894089a0638e68a07c945a32c9e14$' "Gradle distribution checksum must match Gradle 9.6.1"

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
