# Customizing Container Builds

By default Forge will automatically discover and build containers in
the source tree of your service. You can customize several aspects of
this by using the `containers` property of your service descriptor.

## Default Behavior

Any file named "Dockerfile" will be built using the containing
directory as context. For example, consider the following source code
layout:

```
<root>
  |
  +---service.yaml
  |
  +---Dockerfile
  |
  +---src/...
```

Given the above service, Forge will (by default) automatically build a
container as follows:

```sh
docker build <root> -f <root>/Dockerfile
```

If you have multiple Dockerfiles in your service, then Forge will
build multiple containers:

```
<root>
  |
  +---service.yaml
  |
  +---Dockerfile
  |
  +---src/...
  |
  +---module/Dockerfile
  |
  +---module/src/...
```

For example, given the service illustrated above, Forge will (by
default) build two containers with the following docker commands:

```sh
docker build <root> -f <root>/Dockerfile
docker build <root>/module -f <root>/module/Dockerfile
```

## Customizing which Containers are built

If you want to override the default container discovery process and
explicitly specify your service containers, you can do so using the
`containers` property of your service descriptor. For example,
consider the following service:

```
<root>
  |
  +---service.yaml
  |
  +---Dockerfile
  |
  +---src/...
  |
  +---module/Dockerfile
  |
  +---module/src/...
```

Normally Forge would build two containers for the above service, but
if we specify the following in our service descriptor, then Forge will
only build the root container:

```yaml
name: my-service
containers:
  - Dockerfile
```

## Customizing the build Context

The `containers` property can also be used to customize *how*
containers are built. For example, if the container in the module
subdirectory needs access to files in the root of the project when
being built, you can enable this by specifying the build context in
service.yaml:

```yaml
name: my-service
containers:
  - Dockerfile
  - dockerfile: module/Dockerfile
    context: .
```

The build context is specified as a path relative to the service root
(the directory containing the service.yaml descriptor). This will
result in the following container builds:

```sh
docker build <root> -f <root>/Dockerfile
docker build <root> -f <root>/module/Dockerfile
```

Note the customized context supplied to the second container build.

## Customizing build Arguments

The `containers` property can be used to customize build arguments as well:

```yaml
name: my-service
containers:
  - Dockerfile
  - dockerfile: module/Dockerfile
    context: .
    args:
      version: '1.0'
```

The service descriptor above will result in the following container
builds:

```sh
docker build <root> -f <root>/Dockerfile
docker build <root> -f <root>/module/Dockerfile --build-arg version='1.0'
```

Note the additional build arguments supplied in the second container build.

## Enabling incremental builds

Building your source code inside your docker container is a great way
to have both a completely consistent and very portable build
environment. Unfortunately this can significantly slow down container
build times with compiled languages, since every container build ends
up doing a clean build of all your source code even if you only change
a single line of code.

Forge can be configured to perform incremental container builds for
this sort of service thereby letting you enjoy significantly faster
build times in a development context.

For example, consider the following simple spark service that is built
by Gradle:

```
<root>
  |
  +---service.yaml
  |
  +---Dockerfile
  |
  +---gradlew
  |
  +---gradlew.bat
  |
  +---gradle/...
  |
  +---settings.gradle
  |
  +---build.gradle
  |
  +---src/main/java/sparkexample/Hello.java
```

We can write a normal `Dockerfile` for this service that builds and
runs our code:

```
FROM openjdk:alpine
WORKDIR /code
COPY . ./
RUN ./gradlew package
ENTRYPOINT ["java", "-jar", "build/libs/hello-spark.jar"]
```

Then, by specifying the `rebuild` metadata for the container
definition in our service descriptor, we can tell forge how to perform
fast incremental rebuilds:

```yaml
name: hello-spark
containers:
 - dockerfile: Dockerfile
   rebuild:
     root: /code
     command: ./gradlew package
     sources:
       - build.gradle
       - settings.gradle
       - src
```

Forge performs incremental rebuilds by copying any modified files
inside your container, executing a command, and then (if the rebuild
is successful) snapshotting that container into an image. The
`rebuild` metadata gives forge the necessary information to do
this:

- The `root` property tells forge where your source code lives inside
  your container.

- The `sources` property tells forge which files should be copied into
  your container. You can specify individual files or directories.

- The `command` property tells forge what command to execute inside
  the container in order to perform a rebuild.

You can see a complete working example of this [here](https://github.com/datawire/forge/tree/master/examples/java-gradle-spark). In this particular case, the
non incremental container build takes roughly 24 seconds (YMMV
depending on network speed) as compared to approximately 3.5 seconds
for the incremental container build.

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
