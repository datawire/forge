# Forge Metadata

Forge automatically adds metadata to every kubernetes resource it
creates.

It adds the following kubernetes `annotations` to each resource:

- `forge.repo` contains the git repo from which the resource was
  deployed. This is computed from the url for the git remote named
  origin. If the resource was deployed from a checkout that has no
  remote named origin, or if it was deployed from a non-git directory,
  then this will be blank.

- `forge.descriptor` contains the path within the repo

- `forge.version` contains the forge computed version of the
  resource. For resources deployed from a clean git checkout, this
  will be `<commitish>.git`.

It adds the following kubernetes `labels` to each resource:

- `forge.service` contains the name of the service as specified in the
  forge service descriptor (`service.xml`)

- `forge.profile` contains the name of the
  [profile](docs/reference/profiles.md) to which the resource belongs.

By using these labels you can easily query and/or cleanup services
you've deployed with forge:

    # list all the k8s resources belonging to myservice
    kubectl get all -o name -l forge.service=myservice

    # delete the dev profile
    kubectl delete all -l forge.service=myservice -l forge.profile=foo

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
