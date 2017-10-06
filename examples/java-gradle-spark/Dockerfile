FROM openjdk:alpine
WORKDIR /code
COPY . ./
RUN ./gradlew package
ENTRYPOINT ["java", "-jar", "build/libs/hello-spark.jar"]
