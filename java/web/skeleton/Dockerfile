FROM docker.io/gradle:8.14.2-jdk21-alpine AS build
WORKDIR /build

COPY settings.gradle .
COPY service service

RUN gradle service:build --no-daemon

FROM registry.access.redhat.com/ubi8/openjdk-21:1.21
WORKDIR /
COPY --from=build /build/service/build/libs/service-*-SNAPSHOT.jar /service.jar
COPY service/src/main/resources/application.yaml /application.yaml

CMD ["java", "-jar", "service.jar"]

EXPOSE 8080 8081
