---
layout: doc
weight: 5
title: "Using forge with istio"
categories: reference
---

Forge can automatically produce istio ready manifests if you have
istioctl installed.

You can install istio by following the instructions
[here](https://istio.io/docs/tasks/installing-istio.html).

Once istio is installed, you can use the istio property in
`service.yaml` to enable its use:

```
name: hello-forge  # name of the service
istio: true        # when true, apply istioctl kube-inject to all manifests
...
```

That's all. Your service is now istio enabled.
