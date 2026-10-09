FROM docker.io/gradle:9.8.0-jdk26-noble@sha256:7168b9b65175d776d2a186d23647383625284f9ec7df59873a47d9be0d1b58e7 AS build
WORKDIR /build
COPY . .
RUN ./gradlew testClasses --no-daemon
ARG UNIT_TEST_NONCE=manual
RUN test -n "$UNIT_TEST_NONCE" && ./gradlew build --no-daemon --rerun-tasks
FROM docker.io/eclipse-temurin:26.0.2.1_1-jre-noble
WORKDIR /app
COPY --from=build --chown=10001:10001 /build/build/libs/notes-backend-0.0.1-SNAPSHOT.jar app.jar
USER 10001:10001
EXPOSE 8080 8081
CMD ["java", "-jar", "app.jar"]
