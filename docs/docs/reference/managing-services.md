# Managing Services

Forge provides several commands for inspecting and managing the
kubernetes resources of services deployed using forge. (Please note
that these commands depend on the [metadata](metadata.md) feature
added in forge 0.4. No harm will come from running these commands if
that metadata is not present, the commands simply will not see or act
upon those resources. If you wish to add this metadata to resources
deployed with an older version of forge, simply redeploy with version
0.4 or later.)

## Inspecting deployed services

Forge automatically tags all kubernetes resources it creates with
[metadata](metadata.md) in the form of labels and annotations. You can
use the `forge list` command to provide a summary of every service in
your cluster that forge has deployed.

The `forge list` output will, for each deployed profile of a service,
display the URL for the source repo, the descriptor and version from
which the source was deployed, as well as all the kubernetes resources
and a summary of their status:

    <service>[<profile>]: <url> | <descriptor> | <version>
      <kind> <namespace>.<name>:
        <status>
      ...

For example:

    $ forge list
    hello-forge[dev]: https://gitub.com/datawire/hello-forge.git | service.yaml | 3d2acb34c0d1658f7c17a2ea008cea83c7fe09ee.git
      deployment default.hello-forge-dev:
        Deployment has minimum availability.
      service default.hello-forge-dev:
        READY(192.168.225.2:80, 192.168.225.3:80, 192.168.225.4:80)

## Deleting deployed services

You can use the `forge delete` command to remove kubernetes resources
that have been deployed by forge. Use the `forge delete <service> <profile>`
form to remove just the resources associated with a single profile,
e.g.:

    $ forge delete hello-forge dev
    
Or if you want to remove all the profiles for a given service, use
`forge delete <service>`, e.g.:

    $ forge delete hello-forge

You can also remove all kubernetes resources deployed by forge with
the `forge delete --all` flag, e.g.:

    $ forge delete --all # please use this carefully!

No variants of the `forge delete` command will have any impact on
kubernetes resources that were not deployed by forge.

## Moving and/or renaming resources

You can use the `--prune` option to ask `forge deploy` to clean up old
resources when you make changes to your k8s manifests. For example, if
you rename or remove resources from your manifests, then `forge deploy
--prune` will pass along the `--prune` option to `kubectl apply`,
along with appropriate filters to limit the scope of the prune to the
current service and profile, thereby causing all the old resources to
be cleaned up, e.g.:

    $ forge deploy --prune

Please note that this functionality depends on the service name
(specified in forge's service.yaml file) remaining the same as this is
how forge resources are labeled. If you wish to rename the service,
you can simply use a regular `forge deploy` and then do a `forge
delete` on the old service name.

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
