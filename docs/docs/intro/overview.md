# Introduction to Forge

Forge is a tool that lets you define and run containerized applications in Kubernetes, from source code. Forge is designed with microservices in mind. With Forge, you:

1. Define how each of your services is built with a Dockerfile.
2. Define how each of your services is run, with a Kubernetes manifest.
3. Define the services that make up your application, with a `service.yaml` file. A sample `service.yaml` file looks like:

   ```
   name: ratings   # the name of this service
   requires:       # the name of any services necessary for this service to function
   - users
   - products
   ...
   ```

4. Run `forge deploy` to build and deploy your services to Kubernetes.

## Forge principles

Forge is built on the following core principles:

* A developer should be able to `forge deploy` from anywhere in their source repository, and the right thing will happen, safely.
* Nothing special happens in CI/CD. CI just does what any developer does by hand.
* Deploys should be as fast as possible, even when deploying hundreds of services.

## Why Forge?

Kubernetes is great for running containerized applications -- from binaries. But in order to run an application from source in Kubernetes, you need to:

* docker build
* compute image name
* docker tag with image name
* docker push to a registry
* write a Kubernetes manifest, with the image name
* apply the Kubernetes manifest

You then need to repeat this for every service of your application, which also means you need a way to manage dependencies. You also want this to run quickly, which means support for incremental builds, caching, and the like.

Forge has been designed from the get go to support networks of services (i.e., microservices applications). It has extensive support for multiple users, multiple languages, and multiple services.

## Features

Forge includes the following features:

* **Dependency management** Forge will build and deploy your application and all of its dependencies into Kubernetes.

* **Templating** Use Jinja2 templates with your Kubernetes manifest files. A typical model is for your operations team to write standard Kubernetes manifest files for use by development, while developers fill in the service-specific information in the `service.yaml` file.

* **Fast** Forge includes a number of features to accelerate deployment, including parallel builds, incremental builds, and request caching.

* **Profiles** Forge lets you create and define custom profiles, which let you customize how you deploy your service(s) to a given environment (e.g., QA, staging, production).

* **Plug-in support** Forge includes support for additional plug-ins that run as part of the build/deploy process. An example plug-in is Forge's support for Istio.

* **100% client-side** Forge is installed as a single binary that runs client-side. There are no additional components to add to your cluster.

* **Image tag management** Forge automatically manages your image tags, and provides full traceability from source to production.

* **No lock-in** Forge's core abstractions are Dockerfiles and Kubernetes manifests, so it's easy for you to adopt Forge into your existing workflow and tools.

## Use cases

Some of the common use cases for Forge include:

### Development environments

If you're a developer, you need to run *and update* your application in an isolated environment. With Forge, a single command will deploy your latest source code and get it running in Kubernetes, with all of your dependencies.

### Automated testing environments

Automated, end-to-end testing can be an important part of a continuous deployment strategy. With Forge, you can easily and repeatably create an isolated test environment containing your application.

## Forge development

Forge is under active development. For information about the latest release, see the [CHANGELOG](../reference/changelog.html).

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
