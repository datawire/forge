---
layout: doc
weight: 2
title: "Forge vs other software"
categories: discussion
---

Forge tackles a variety of long-standing problems with developing services on Kubernetes. Individual features of some existing solutions address the same set of problems as Forge. This section contrasts Forge with other solutions.

## CI/CD systems

A CI/CD pipeline such as Jenkins or Travis is typically used to code from source control to a Kubernetes cluster.

Forge differs from Jenkins/Travis/etc in a few ways:

* Forge is designed to run without requiring a commit, e.g., you want to test a specific code change before committing
* Forge runs entirely client-side, without requiring a server
* Jenkins/Travis/etc do not directly deploy code into a Kubernetes cluster. Instead, they rely on you writing a custom script to create a Kubernetes manifest and deploy the code. Forge has a templating system that lets you create your own Kubernetes manifests.

One of the reasons why Forge is designed to run entirely client-side is to facilitate easy integration with a CI system. Forge can be invoked as part of your CI/CD pipeline post-commit to automatically package/deploy a service into a Kubernetes cluster.

## Docker Compose

Docker Compose is a popular choice to create isolated development environments on a local system. With Docker Compose, a set of services can be easily deployed as a group on your laptop for development.

Similar to Compose, Forge can deploy a set of services as a group for easy development. Forge differs in a few different ways from Compose:

* Forge targets Kubernetes clusters only, whether locally (via minikube) or remote Kubernetes clusters.
* Forge is designed so that developers can use the same workflow for development and production. With Docker Compose, a different workflow is required for production deployment, which introduces possible environmental differences (and hard-to-reproduce bugs).
