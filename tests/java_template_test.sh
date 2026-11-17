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
check_file_contains "$base/Dockerfile" 'gradle:9\.9\.1-jdk27-resolute' "build image must use JDK 27"
check_file_contains "$base/Dockerfile" 'eclipse-temurin:27\.0\.1\.0-jre-resolute' "runtime image must match .java-version"
check_file_contains "$base/gradle/wrapper/gradle-wrapper.properties" '^distributionSha256Sum=d8a18a7a841dd5df825d35a685fad6f2d7f12ac0c280e57b67c27b4a520ba228$' "Gradle distribution checksum must match Gradle 9.9.1"

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
