# Forge

You have source code. You want to get it running.

The typical way you'd typically do this is to use a build system, which will take your source code and produce a binary that you can then run.

However, in cloud applications, "running a binary" has become much more complex. You can (and should) specify how much memory and CPU your binary needs. You can (and should) specify how to upgrade your binary (e.g., a canary deployment). You can (and should) specify how many servers you want to run on, for availability or scalability.

Your build system wasn't designed to build cloud applications.

Forge is a build system for microservices.

Forge:

1. Produces deployable artifacts from source code.
2. Manages your runtime dependencies.

## Example

Your `forge.yaml` specifies the basic information needed to build your service.

```
# forge.yaml
name: cookie    # Service name
prefix: cookie  # URL prefix
memory: 0.5G    # Maximum memory
cpu: 0.25       # Maximum CPU
```

Then, you can just build and deploy your service.

```
% forge build     # build deployable binaries of the software
% forge deploy    # deploy the service(s) to the target Kubernetes cluster
```

## Forge compared to ...

### Docker

Docker encapsulates a service and its dependencies in a container. Docker does not support service-to-service dependencies, nor does it support metadata about deployment.

Forge uses Docker internally as a core deployment abstraction.

### Docker Compose

Docker Compose extends Docker to support service-to-service dependencies. Docker Compose does not support metadata about deployment.

### Helm

Helm is a popular format for managing Kubernetes applications (aka charts). The Helm format natively supports metadata about deployment. Helm does not include a build system of any sort.

### Maven, Gradle, Make, Bazel, Pants, ...

These build systems are all designed for creating binaries. Forge delegates to your build system of choice when actually compiling your service.

## More about Forge

The forge project contains development and deployment tooling for
working with microservices applications on top of kubernetes.

Using kubernetes to run a microservices style application (a service
mesh) generally involves a number of rapidly moving parts:

 - Kubernetes holds your live service mesh.
 - Your container registry holds your runnable artifacts for all the services in your mesh.
 - Git holds the source code for all your services.

Actually getting source code running on kubernetes involves checking
out your service code, baking a container for it, taging and pushing
that container to the right place, and updating the necessary
kubernetes resources.

You can encode this process in a bespoke pipeline, but then it gets
really hard to replicate if you want to spin the service mesh up in
another cluster.

Forge provides a convenient and easy primitive that makes this
consistent, fast, and safe, and *repeatable*. Forge sits in the
middle of all these and provides a fast, consistent, and safe way to
keep all of these in sync.

## Installing

```
curl -sL https://raw.githubusercontent.com/datawire/forge/master/install.sh | INSTALL_DIR=${HOME}/forge sh
```

## Getting Started

Forge can automatically pull the source code for all the services
necessary to run your whole mesh. You can try this with the twitface
organization:

```
mkdir work
cd work
forge pull twitface
```

*Note:* By default, forge operates on the current directory. If
you want you can pass an alternative directory via the --workdir
parameter.

*Note:* if you want to use a private organization, you will need to
create and supply a github access token

Forge can bake any containers not already in your registry:

```
forge bake registry.hub.docker.com/<repo> --user <docker-user> --password <docker-password>
```

Forge can push any containers not already in the registry:

```
forge push registry.hub.docker.com/<repo> --user <docker-user> --password <docker-password>
```

Forge can deploy all your services into kubernetes. This uses
whatever cluster kubectl is currently pointing to, so lets do a
dry-run first just to be safe:

```
forge deploy registry.hub.docker.com/<repo> --dry-run
```

Do it for realz:

```
forge deploy registry.hub.docker.com/<repo>
```

That's it! This works the same way whether you have 5 services or
50. You can use the command line version of forge to run your
service mesh in your own isolated dev cluster, or you can deploy
forge as a service and register a github hook to provide a
complete deployment pipeline:

```
forge serve
```
