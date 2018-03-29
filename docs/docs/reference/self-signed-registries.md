# Forge Metadata

In order to use Forge with a self-signed registry, you need to disable
verification. In order to do this, you need to create a `forge.yaml` by
hand rather than using the `forge setup` command. Put the following
yaml into a file named `forge.yaml` in the directory (or a parent of
the directory) where you would like to use Forge:

```
registry:
  type: docker
  url: self-signed-registry.example.com
  verify: false
  namespace: your-namespace
```

Replace the `self-signed-registry.example.com` and the
`your-namespace` with your own values. You should now be able to use
forge with a self-signed registry.

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
