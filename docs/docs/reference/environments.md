# Environment Customization

You can tailor your deployments to a given profile (e.g. dev, staging,
or production) by using environment variables. The environment is
exposed to the `service.yaml` file via the `env` variable:

{% raw %}
```yaml
name: my-service

targetPort: {{env.TARGET_PORT or 8080}}
memory: {{env.MEMORY or "1G"}}
cpu: {{env.CPU or 0.5}}
```
{% endraw %}

This same `env` variable is also available in the kubernetes templates
underneath the `k8s` directory in your service source tree.

In order to enable easier customization, forge will search upwards
from the current directory for any `.env` files and default
environment variables based on the contents of the first `.env` file
found.

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**