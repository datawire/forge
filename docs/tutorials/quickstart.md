---
layout: doc
weight: 1
title: "Get started with Forge"
categories: tutorials
---

<link rel="stylesheet" href="{{ "/css/mermaid.css" | prepend: site.baseurl }}">
<script src="{{ "/js/mermaid.min.js" | prepend: site.baseurl }}"></script>
<script>mermaid.initialize({
   startOnLoad: true,
   cloneCssStyles: false,
 });
</script>

# Get started with Forge

## Installation

Forge has been tested on Mac OS X, Fedora 25, and Ubuntu 16.04. To get started, you're going to need the following installed on your system:

* Docker
* kubectl, with access to a Kubernetes cluster (minikube is fine)
* a Docker registry

You can install Forge via `curl`:

```
curl -sL https://raw.githubusercontent.com/datawire/forge/master/install.sh | INSTALL_DIR=${HOME}/forge sh
```

## Configuration

2. Once forge is installed, we can configure it using `forge setup`:

```
mkdir forge-quickstart
cd forge-quickstart
forge setup
```

## Deploy a service

3. Forge lets you deploy a service into Kubernetes in a single command, `forge deploy`.

```
git clone https://github.com/datawire/hello-forge.git
forge deploy # builds, pushes, and deploys the service onto kubernetes
```

4. Once forge deploy completes, you can type kubectl get services to
   get the IP address of the myservice.

*Note* on minikube, use `minikube service --url hello-forge` instead
       of `kubectl get services`

```
kubctl get services
NAME         CLUSTER-IP      EXTERNAL-IP       PORT(S)        AGE
hello-forge  10.91.248.98    XXX.XXX.XXX.XXX   80:30651/TCP   4m
...
```

5. curl to the `XXX.XXX.XXX.XXX` IP address, and see Hello, World!.


```
curl XXX.XXX.XXX.XXX
Hello World! ...
```

## Change the service

1. You've discovered your service is on Hacker News, and you want to bump up the memory. Take a look at the `service.yaml` file:

```
name: hello-forge
memory: 0.25G
cpu: 0.25
```

2. Edit the memory from 0.25G to 0.5G.

3. Now, let's change some source code:

```
sed -i -e 's/Hello World!/Hey-Diddley-Ho!!!/' hello-forge/app.py
forge deploy
```

7. Now we can curl and see the new message (kubernetes may take a few
   seconds to rollout the new image):

```
curl XXX.XXX.XXX.XXX
Hey-Diddley-Ho!!! ...
```

8. So now we've seen we can easly build and deploy a single service,
   but microservices are only useful when you can get a whole bunch of
   them to work together. Using forge we can just as easily spin up a
   whole network of microservices:

```
git clone https://github.com/datawire/hello-forge-network.git
forge deploy
```

9. Now let's see all our services:

```
kubectl get services
...
```
