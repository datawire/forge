---
layout: doc
weight: 2
title: "Introduction to Forge"
categories: introduction
---

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

## Why Forge?

Kubernetes is great for running containerized applications -- from binaries. But in order to run an application from source in Kubernetes, you need to:

* docker build
* compute image name
* docker tag with image name
* docker push to a registry
* write a Kubernetes manifest, with the image name
* apply the Kubernetes manifest

You then need to repeat this for every service of your application, which also means you need a way to manage dependencies. You also want this to run quickly, which means support for incremental builds, caching, and the like.

## Features

Forge includes the following features:

* **Dependency management** Forge will build and deploy your application and all of its dependencies into Kubernetes.

* **Templating** Use Jinja2 templates with your Kubernetes manifest files. A typical model is for your operations team to write standard Kubernetes manifest files for use by development, while developers fill in the service-specific information in the `service.yaml` file.

* **Fast** Forge includes a number of features to accelerate deployment, including parallel builds, incremental builds, and request caching.

* **Plug-in support** Forge includes support for additional plug-ins that run as part of the build/deploy process. An example plug-in is Forge's support for Istio.

## Use cases

Some of the common use cases for Forge include:

### Development environments

If you're a developer, you need to run *and update* your application in an isolated environment. With Forge, a single command will deploy your latest source code and get it running in Kubernetes, with all of your dependencies.

### Automated testing environments

Automated, end-to-end testing can be an important part of a continuous deployment strategy. With Forge, you can easily and repeatably create an isolated test environment containing your application.


## Forge development

Forge is under active development. For information about the latest release, see the [CHANGELOG](../reference/changelog.html).
