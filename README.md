# Forge

Forge is a build system for microservices running on kubernetes
(k8s). This means two things:

1. It produces fully deployable artifacts (docker images + k8s yaml).
2. It understands service dependencies.

## Quickstart

In this quick start, we'll walk through the basic functionality of
Forge.

1. First, let's make sure you have all the requisite dependencies. You
   will need:

* Docker
* kubectl, with access to a Kubernetes cluster (minikube is fine)
* a Docker registry

2. Now let's install forge:

```
curl -sL https://raw.githubusercontent.com/datawire/forge/master/install.sh | INSTALL_DIR=${HOME}/forge sh
```

3. Once forge is installed, we can configure it using `forge setup`:

```
mkdir forge-quickstart
cd forge-quickstart
forge setup
```

4. Now let's build a service:

```
git clone https://github.com/datawire/hello-forge.git
forge bake # bakes a docker image of our service
forge push # pushes the docker image to the configured repo
forge deploy # deploys the service on kubernetes
```

5. Once forge deploy completes, you can type kubectl get services to get the IP address of the myservice.

```
kubctl get services
NAME         CLUSTER-IP      EXTERNAL-IP       PORT(S)        AGE
hello        10.91.248.98    XXX.XXX.XXX.XXX   80:30651/TCP   40d
...
```

6. curl to the `XXX.XXX.XXX.XXX` IP address, and see Hello, World!.

```
curl XXX.XXX.XXX.XXX
Hello World! ...
```

7. Now, let's change some source code:

```
sed -i -e 's/Hello World!/Hey-Diddley-Ho!!!/' hello-forge/app.py
forge bake && forge push && forge deploy
```

8. Now we can curl and see the new message (kubernetes may take a few seconds to rollout the new image):

```
curl XXX.XXX.XXX.XXX
Hey-Diddley-Ho!!! ...
```

9. So now we've seen we can easly build and deploy a single service,
   but microservices are only useful when you can get a whole bunch of
   them to work together. Using forge we can just as easily spin up a
   whole network of microservices:

```
git clone https://github.com/datawire/hello-forge-network.git
forge bake && forge push && forge deploy
```

10. Now let's see all our services:

```
kubectl get services
...
```
