# Skunkworks

The skunkworks project contains development and deployment tooling for
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

Skunkworks provides a convenient and easy primitive that makes this
consistent, fast, and safe, and *repeatable*. Skunkworks sits in the
middle of all these and provides a fast, consistent, and safe way to
keep all of these in sync.

## Installing

```
curl -sL https://raw.githubusercontent.com/datawire/skunkworks/master/install.sh | INSTALL_DIR=${HOME}/skunkworks sh
```

## Getting Started

Skunkworks can automatically pull the source code for all the services
necessary to run your whole mesh. You can try this with the twitface
organization:

```
mkdir work
cd work
sw pull twitface
```

*Note:* By default, skunkworks operates on the current directory. If
you want you can pass an alternative directory via the --workdir
parameter.

*Note:* if you want to use a private organization, you will need to
create and supply a github access token

Skunkworks can bake any containers not already in your registry:

```
sw bake registry.hub.docker.com/<repo> --user <docker-user> --password <docker-password>
```

Skunkworks can push any containers not already in the registry:

```
sw push registry.hub.docker.com/<repo> --user <docker-user> --password <docker-password>
```

Skunkworks can deploy all your services into kubernetes. This uses
whatever cluster kubectl is currently pointing to, so lets do a
dry-run first just to be safe:

```
sw deploy registry.hub.docker.com/<repo> --dry-run
```

Do it for realz:

```
sw deploy registry.hub.docker.com/<repo>
```

That's it! This works the same way whether you have 5 services or
50. You can use the command line version of skunkworks to run your
service mesh in your own isolated dev cluster, or you can deploy
skunkworks as a service and register a github hook to provide a
complete deployment pipeline:

```
sw serve XXX-TODO
```
