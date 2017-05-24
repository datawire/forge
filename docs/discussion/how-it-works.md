---
layout: doc
weight: 2
title: "How it works"
categories: discussion
---

Forge builds services based on Docker and Kubernetes. It assumes the
output of any service build consists of one or more docker containers
along with the kubernetes yaml necessary to spin up these containers.
The build process consists of the following stages:

1. Find service definitions.
2. Compute versions for all input sources.
3. Build, tag, and push any missing containers.
4. Build and apply the kubernetes yaml.

## Finding Services
Forge finds services by searching the filesystem for any file named
`service.yaml`. Any directory containing such a file is assumed to
following a standard layout:
```
  root
    |
    +-- service.yaml    # identifies this directory as a service and contains key metadata
    |
    +-- k8s/*           # deployment templates (jinja2)
    |
    +-- **/Dockerfile   # one or more container definitions
```
## Computing Versions

Forge automatically computes a version for any service it builds. If
the service is located in an *unmodified* git tree, forge will use
`<commit>.git` as the version. If the service is not located in a git
tree, or the git tree has changes, forge will compute the sha1 hash of
the filesystem tree for all the services and use a version of the form
`<sha1hash>.ephemeral`. This enables forge to be conveniently used for
dev builds, but also retains complete traceability for production
builds.

## Building Containers
Forge computes canonical container image names based on the configured
docker registry, repo, and the computed service names. It then queries
for the existence of these canonical images both remotely and locally,
and if necessary it invokes `docker build` in order to build, tag, and
push missing containers.
*Note* if you are wondering how to avoid including lots of build tools
 in your containers, check out docker's
 [multi-stage builds](https://docs.docker.com/engine/userguide/eng-image/multistage-build/).

## Building Kubernetes yaml
The kubernetes yaml necessary to deploy the containers associated with
a service is produced from the jinja2 templates in the `k8s`
directory. These templates are invoked with both the service metadata
(contents of `service.yaml`), as well as the build metadata.
Template variables:
```
  service
    |
    +-- name   # this is defaulted based on directory name if not explicitly specified in service.yaml
    |
    +-- ...    # any other variables defined in service.yaml
  build
    |
    +-- images # map from Dockerfile relative path to built image name
```
After generating the kubernetes yaml for all services, forge validates
the yaml and ensures that there are no resource name conflicts between
services.
