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
check_file_contains "$base/Dockerfile" 'gradle:9\.8\.1-jdk27-resolute' "build image must use JDK 27"
check_file_contains "$base/Dockerfile" 'eclipse-temurin:27_35-jre-resolute' "runtime image must match .java-version"
check_file_contains "$base/gradle/wrapper/gradle-wrapper.properties" '^distributionSha256Sum=dce76f55f8e251a3a1f130eb120f30b3d271de2b76c9b0729d316b5a1b6dc01f$' "Gradle distribution checksum must match Gradle 9.8.1"

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
