# Service descriptor

Each service managed by Forge includes key metadata about the service in the `service.yaml` file. This is known as the *service descriptor*.

The `service.yaml` contains information about:

* Values that are instantiated into Kubernetes manifests
* [Dependencies](dependencies.md)
* Information about [profiles](profiles.md), a way to apply different values into your Kubernetes manifests depending on your target context (e.g., QA, production, development)
* Information on how to map specific Git branch policies to a given profile

Below is an example `service.yaml`:

```
{% raw %}
{% set sanitized_branch = (branch or "dev").replace('/', '-') %}
{% endraw %}

name: python-api
namespace: datawire

profiles:
  stable:
    endpoint: /python-api
    max_memory: 0.1G
    max_cpu: 0.1
  canary:
    endpoint: /python-api
    weight: 50 # percentage of traffic to route to this class of deployment
    max_memory: 0.1G
    max_cpu: 0.1
  default:
    name: {{sanitized_branch}}
    endpoint: /{{sanitized_branch}}/python-api
    max_memory: 0.1G
    max_cpu: 0.1

branches:
  master: stable
  dev/*: default
```


**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
