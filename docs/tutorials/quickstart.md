---
layout: doc
weight: 1
title: "Forge Quickstart"
categories: tutorials
---

## Prerequisites

Forge has been tested on Mac OS X, Fedora 25, and Ubuntu 16.04. To get started, you're going to need the following installed on your system:

* Docker ([Mac OS X](https://docs.docker.com/docker-for-mac/),  [Ubuntu](https://docs.docker.com/engine/installation/linux/ubuntu/), [Fedora](https://docs.docker.com/engine/installation/linux/fedora/) install instructions)
* kubectl, with access to a Kubernetes cluster (minikube is fine)
* a Docker registry, such as Docker Hub or Google Container Registry
* A working Python environment with `virtualenv` installed

If you don't have `virtualenv` installed, you can install it with `pip install virtualenv`.

## Installing Forge

Once you have the prerequisites installed, you can install Forge via `curl`:

```
curl -sL https://raw.githubusercontent.com/datawire/forge/master/install.sh | INSTALL_DIR=${HOME}/forge sh
```

## Configuration

Create a working directory for Forge and run `forge setup` to complete the installation. Setup will ask for authentication information to a Docker Registry as part of this process:

```
mkdir forge-quickstart
cd forge-quickstart
forge setup
```

## Deploy a service

When deploying a service into Kubernetes, you need to provide not just code, but the actual <strong>configuration</strong> needed to run this code. Forge is a build/deployment system that builds both the code and configuration, together.

1. We'll show Forge in action with a simple service. Clone our example service:

   ```
   git clone https://github.com/datawire/hello-forge.git
   ```

2. In the example service, you'll see a `service.yaml` file. This file contains the basic runtime configuration for the service.

   ```yaml
   name: hello-forge
   memory: 0.25G
   cpu: 0.25
   ```

3. Normally, if you want to get a service running in Kubernetes, you need to   build a Docker image, push the image to a Docker registry, write some Kubernetes YAML, and run `kubectl` to get the service running.

   With Forge, the `deploy` command will take care of everything you need to get the service running. Try it now:  

   ```
   forge deploy
   ```

4. Once `deploy` completes, you can type `kubectl get services` to
   get the IP address of the service.

   *Note* on minikube, use `minikube service --url hello-forge` instead of `kubectl get services`

   ```
   $ kubctl get services
   NAME         CLUSTER-IP      EXTERNAL-IP       PORT(S)        AGE
   hello-forge  10.91.248.98    XXX.XXX.XXX.XXX   80:30651/TCP   4m
   ...
   ```

5. curl to the `XXX.XXX.XXX.XXX` IP address, and see "Hello, World!".


   ```
   $ curl XXX.XXX.XXX.XXX
   Hello World! ...
   ```

6. You can also verify that the limits specified in the `service.yaml` file are in effect with `kubectl describe pod XXX`.

## Change the service

1. You've discovered your service is on Hacker News, and you want to bump up the memory and change your greeting. Edit the `service.yaml` file and change the memory to 0.5G. ProTip: if you don't specify a limit, Kubernetes will default to unlimited ... which will enable an errant service to take down your entire cluster.

   So let's change some source code and redeploy:

   ```
   sed -i -e 's/Hello World!/Hello Hacker News!!!/' hello-forge/app.py
   forge deploy
   ```

2. Now you can curl and see the new message (Kubernetes may take a few
   seconds to rollout the new image):

   ```
   $ curl XXX.XXX.XXX.XXX
   Hello Hacker News!!! ...
   ```

3. You can verify that the service does have more memory with `kubectl describe pods`, as above.

## A network of services

1. So now we've seen we can easily build and deploy a single service,
   but microservices are truly useful when you can get a whole bunch of
   them to work together. Using Forge we can just as easily spin up a
   whole network of microservices:

   ```
   git clone https://github.com/datawire/hello-forge-network.git
   forge deploy
   ```

2. You can see Forge has built, pushed, and deployed the entire network of services.

   ```
   kubectl get services
   ```

## Next steps

You've seen an example of how Forge can quickly build and deploy services to Kubernetes. Now, try setting up <a href="using-forge.html">Forge on your own services</a>.
