# Forge vs other software

Forge tackles a variety of long-standing problems with developing services on Kubernetes. Individual features of some existing solutions address the same set of problems as Forge. This section contrasts Forge with other solutions.

## Docker Compose

Forge is perhaps most similar to Docker Compose. With Docker Compose, a set of services can be easily deployed as a group on your laptop for development. The primary difference between Forge and Compose is that Forge is designed for Kubernetes. In practice this means:

* Forge automates building a docker image (like Compose), but also tagging the image, pushing the image into a registry, and updating the Kubernetes manifest to include the registry (steps not necessary with a Docker-only environment)
* Forge supports full-blown Kubernetes manifests

## Kompose

Kompose converts Docker Compose to Kubernetes. Kompose will convert existing Docker Compose files to Kubernetes manifests. Forge differs from Kompose in two basic ways:

* Forge automates the process of deploying source into Kubernetes
* Kompose relies on the semantics of Docker Compose, which do not support the full range of Kubernetes semantics

## CI/CD systems

A CI/CD pipeline such as Jenkins or Travis is typically used to code from source control to a Kubernetes cluster.

Forge differs from Jenkins/Travis/etc in a few ways:

* Forge is designed to run without requiring a commit, e.g., you want to test a specific code change before committing
* Forge runs entirely client-side, without requiring a server
* Jenkins/Travis/etc do not directly deploy code into a Kubernetes cluster. Instead, they rely on you writing a custom script to create a Kubernetes manifest and deploy the code. Forge has a templating system that lets you create your own Kubernetes manifests.

One of the reasons why Forge is designed to run entirely client-side is to facilitate easy integration with a CI system. Forge can be invoked as part of your CI/CD pipeline post-commit to automatically package/deploy a service into a Kubernetes cluster.

## Helm

Helm is a package manager for Kubernetes. Helm is focused on packaging/distributing Kubernetes services. Forge differs from Helm in a few different ways:

* Forge is focused on the developer workflow (e.g., deploy code without committing), versus packaging/distribution.
* Forge is entirely client-side, and runs on your laptop (Helm, etc. require server-side components).

Forge could be extended to produce Helm charts (see https://github.com/datawire/forge/issues/15 and upvote!).

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**