# Profiles

It is often useful to customize a deployment to a given profile,
e.g. for development you might want to set lower memory and cpu usage
limits than for production. Also for canary deploys, it may be useful
to specify additional routing metadata to ensure that the right amount
of live traffic flows through to your canary deployment.

Forge provides a profile mechanism to help make this easier. Forge
profiles work the following way:

1. You can define any number of profiles in your service.yaml
   file. Each profile can define different values for a given
   property.

2. When forge performs a build, a single profile is chosen based on
   the current git branch. This can be overriden by command line
   arguments and/or environment variables.

3. The properties from the chosen profile are copied into the
   `build.profile` object and may then be used to customize your
   kubernetes yaml as appropriate for that profile.

For example, the following service.yaml defines stable, canary, and
default profiles:

{% raw %}
```yaml
name: my-service

profiles:
  stable:
    max_memory: 0.5G
    max_cpu: 0.5
  canary:
    max_memory: 0.5G
    max_cpu: 0.5
    weight: 1.0 # default to routing 1% of traffic to this deployment
  default:
    max_memory: 0.25G
    max_cpu: 0.25
```
{% endraw %}

The following kubernetes deployment references profile-specific values
such as `build.profile.max_memory` and `build.profile.max_cpu`.

{% raw %}
```yaml
---
apiVersion: v1
kind: Service
metadata:
  name: {{build.name}}
  annotations:
    ambassador: |
      ---
      apiVersion: ambassador/v1
      kind: Mapping
      name: {{build.name}}-mapping
      prefix: /hello/
      service: {{build.name}}
      {%- if "weight" in build.profile %}
      weight: {{build.profile.weight}}
      {%- endif %}
spec:
  selector:
    app: {{build.name}}
  ports:
    - protocol: {{service.protocol|default('TCP')}}
      port: {{service.port|default('80')}}
      targetPort: {{service.targetPort|default('8080')}}
  type: LoadBalancer
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata: {name: {{build.name}}}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{build.name}}
  strategy:
    rollingUpdate: {maxSurge: 1, maxUnavailable: 0}
    type: RollingUpdate
  revisionHistoryLimit: 1
  template:
    metadata:
      labels:
        app: {{build.name}}
      name: {{build.name}}
    spec:
      containers:
      - image: {{build.images["Dockerfile"]}}
        imagePullPolicy: IfNotPresent
        name: {{build.name}}
        resources:
          requests:
            memory: {{build.profile.min_memory|default(0.1)}}
            cpu: {{build.profile.min_cpu|default(0.1)}}
          limits:
            memory: {{build.profile.max_memory}}
            cpu: {{build.profile.max_cpu}}
        terminationMessagePath: /dev/termination-log
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      securityContext: {}
      terminationGracePeriodSeconds: 30
```
{% endraw %}

## Specify profiles for branches

You can further customize how the profile is chosen via the use of the
branch mapping feature of service.yaml. For example, if you wanted to
have multiple simultaneous canaries, the following branches mapping
would map any git branch starting with `canary/` to the canary
profile:

{% raw %}
```yaml
name: my-service

profiles:
  stable:
    max_memory: 0.5G
    max_cpu: 0.5
  canary:
    max_memory: 0.5G
    max_cpu: 0.5
    weight: 1.0 # default to routing 1% of traffic to this deployment
  default:
    max_memory: 0.25G
    max_cpu: 0.25

branches:
  master: stable
  canary/*: canary
```
{% endraw %}

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**
