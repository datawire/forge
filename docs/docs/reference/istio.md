# Using Forge with Istio

Forge can automatically produce Istio ready manifests if you have
istioctl installed.

You can install Istio by following the instructions
[here](https://istio.io/docs/tasks/installing-istio.html).

Once Istio is installed, you can use the Istio property in
`service.yaml` to enable its use:

```
name: hello-forge  # name of the service
istio:
  enabled: true        # when true, apply istioctl kube-inject to all manifests
  includeIPRanges:     # optional list of IP ranges in CIDR form to be passed to istioctl kube-inject
    - 10.0.0.0/8
    - 172.32.0.0/16
...
```

That's all. Your service is now Istio enabled.

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**