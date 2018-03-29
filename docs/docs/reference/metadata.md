# Forge Metadata

Forge automatically adds metadata to every Kubernetes resource it
creates. It adds the following Kubernetes `annotations` to each resource:

- `forge.repo` contains the git repo from which the resource was
  deployed. This is computed from the url for the git remote named
  origin. If the resource was deployed from a checkout that has no
  remote named origin, or if it was deployed from a non-git directory,
  then this will be blank.

- `forge.descriptor` contains the path within the repo

- `forge.version` contains the forge computed version of the
  resource. For resources deployed from a clean git checkout, this
  will be `<commitish>.git`.

It adds the following Kubernetes `labels` to each resource:

- `forge.service` contains the name of the service as specified in the
  forge service descriptor (`service.yaml`)

- `forge.profile` contains the name of the
  [profile](docs/reference/profiles.md) to which the resource belongs.

By using these labels you can easily query and/or cleanup services
you've deployed with Forge:

    # list all the k8s resources belonging to myservice
    kubectl get all -o name -l forge.service=myservice

    # delete the dev profile
    kubectl delete all -l forge.service=myservice -l forge.profile=dev

You can also use the `forge list` command to show a human readable
summary of the Forge resources deployed into a cluster, e.g.:

    $ forge list
    myservice[default]: https://github.com/myorg/myservice.git | service.yaml | 729b401e7c515144bbaf0962b6a207f591f291ca.git
      deployment default.myservice-default:
        Deployment has minimum availability.
      service default.myservice-default:
        READY(192.168.187.194:80, 192.168.187.195:80, 192.168.187.196:80)

    myservice[foo]: https://github.com/myorg/myservice.git | service.yaml | 62334241058f806e1fc26a246f10e78ec1d7abbb.git
      deployment default.myservice-foo:
        Deployment has minimum availability.
      service default.myservice-foo:
        READY(192.168.187.197:80, 192.168.187.198:80, 192.168.187.199:80)


**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
