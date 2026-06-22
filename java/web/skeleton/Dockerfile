FROM docker.io/gradle:9.5.1-jdk25-noble AS build
WORKDIR /build

COPY settings.gradle .
COPY service service

RUN gradle service:build --no-daemon

FROM eclipse-temurin:25-jre-noble
WORKDIR /

# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
  libgcrypt20 \
  libgnutls30t64 \
  liblzma5 \
  libssl3t64 \
  libsystemd0 \
  libudev1 \
  openssl \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build /build/service/build/libs/service-*-SNAPSHOT.jar /service.jar
COPY service/src/main/resources/application.yaml /application.yaml

CMD ["java", "-jar", "service.jar"]

EXPOSE 8080 8081
