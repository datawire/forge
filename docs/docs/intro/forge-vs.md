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

## Skaffold

[Google Skaffold](https://github.com/GoogleCloudPlatform/skaffold) is a relatively new project. Skaffold shares a number of common traits with Forge, e.g., it's a 100% client-side workflow engine that invokes a number of processes to build and deploy your source into Kubernetes.

Forge has extensive support for the multiple developer / multiple microservices scenario (e.g., profiles, dependencies, deployment metadata, fast incremental deploys).

Forge also has first-class support for non-Google Cloud Platform projects.

## Draft

[Draft](https://github.com/azure/draft) is a Helm-based system for continuous deployment of Kubernetes services. Draft uses a client/server model, which imposes additional performance and complexity on your development setup (note: this has changed with the Draft 0.12, released in March 2018).

Draft is tied entirely to Helm v2 (see Helm section below), and inherits all the benefits and challenges of Helm v2.

Draft has language packs that automatically create skeleton applications for you; Forge does not do this at the moment.

Forge has extensive support for the multiple developer / multiple microservices scenario (e.g., profiles, dependencies, deployment metadata, fast incremental deploys). Because of Draft's use of Helm, some of these features are not possible / difficult to do. For example, Forge can do incremental deployments of hundreds of services. Since Draft delegates dependencies to Helm, Draft is not able to do incremental deploys at the source level.

## CI/CD systems

A CI/CD pipeline such as Jenkins or Travis is typically used to code from source control to a Kubernetes cluster.

Forge differs from Jenkins/Travis/etc in a few ways:

* Forge is designed to run without requiring a commit, e.g., you want to test a specific code change before committing
* Forge runs entirely client-side, without requiring a server
* Jenkins/Travis/etc do not directly deploy code into a Kubernetes cluster. Instead, they rely on you writing a custom script to create a Kubernetes manifest and deploy the code. Forge has a templating system that lets you create your own Kubernetes manifests.

One of the reasons why Forge is designed to run entirely client-side is to facilitate easy integration with a CI system. Forge can be invoked as part of your CI/CD pipeline post-commit to automatically package/deploy a service into a Kubernetes cluster.

## Helm

Helm is a package manager for Kubernetes. Helm provides four major functions:

1. Package management. Similar to `apt-get`, `yum`, or `brew`, Helm lets users list, install, uninstall off-the-shelf applications.
2. Application lifecycle management. Deploying new versions of a service, rolling the services back, deleting services.
3. Configuration customization, via Go templating.

Forge does not address the package management use case. Forge is focused on the application lifecycle management and configuration customization at a source level (versus a pre-packaged installation level). Note that Helm is going through a fairly extensive refactoring as of March 2018, and Helm v3 will be substantially different.

Forge could be extended to produce Helm charts (see https://github.com/datawire/forge/issues/15 and upvote!).

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
