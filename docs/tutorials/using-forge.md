---
layout: doc
weight: 2
title: "Using Forge on your services"
categories: tutorials
---
To start using Forge on a new or existing service, follow these steps.

1. Create a deployment template in `$REPO_HOME/k8s`. The deployment template should contain all the necessary information to deploy the service. Forge supports templating the deployment template using the [Jinja2 templating engine](http://jinja.pocoo.org/). Here's a simple example:

{% raw %}
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: {{service.name}}
    spec:
      selector:
        app: {{service.name}}
      ports:
        - protocol: TCP
          port: 80
          targetPort: 5000
      type: LoadBalancer
    ---
    apiVersion: extensions/v1beta1
    kind: Deployment
    metadata: {name: {{service.name}}}
    spec:
      replicas: 1
      selector:
        matchLabels: {app: {{service.name}}}
      strategy:
        rollingUpdate: {maxSurge: 1, maxUnavailable: 0}
        type: RollingUpdate
      revisionHistoryLimit: 1
      template:
        metadata:
          labels: {app: {{service.name}}}
          name: {{service.name}}
        spec:
          containers:
          - image: {{build.images["Dockerfile"]}}
            imagePullPolicy: IfNotPresent
            name: {{service.name}}
            resources:
              limits:
                memory: {{service.memory}}
                cpu: {{service.cpu}}
            terminationMessagePath: /dev/termination-log
          dnsPolicy: ClusterFirst
          restartPolicy: Always
          securityContext: {}
          terminationGracePeriodSeconds: 30
{% endraw %}

    Note how we use templates for values such as the memory and CPU limits.

2. Create a `service.yaml` file in `$REPO_HOME`. This file identifies the service and contains the metadata for deployment. Here's an example that maps to the above example:

    ```
    name: hello
    memory: 0.25G
    cpu: 0.25
    ```

    Each of these values are interpolated into the deployment template above.

3. Create a `Dockerfile` in `$REPO_HOME`. This should specify how the Docker container should be built.

4. That's it! With these 3 files, you can now deploy into Kubernetes with `forge deploy`.
