---
layout: doc
weight: 2
title: "Canary deploys with Kubernetes"
categories: reference
---
People use the term canary deploys to refer to multiple related but
different things. Anything from A/B testing UX features on users, to
the practice of incrementally rolling out code changes in order to
avoid catastrophic failure.

The common theme most of these is to make a (potentially) catastrophic
change in a controlled manner while measuring the impact so as to
minimize negative consequences.

Depending on how impact is measured (e.g. can it be automated or does
it require humans), different approaches are needed, and kubernetes
offers multiple options that can be used in these different cases.

## Incremental updates of a single deployment

Kubernetes has a builtin deployment mechanism that is designed
specifically to update an application to a new version at a controlled
rate. See
[here](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
for details.

This can be leveraged in most cases where automated measurement of
impact is possible. The short story is that when you update any of the
containers associated with your deployment, Kubernetes will
automatically update the running application at a controlled rate
(spin up the new version, measure impact, and the spin down the old
version) based on the parameters set in your deployment definition.

This process can be configured in several ways using the parameters
defined in the deployment specification (see maxSurge, maxUnavailable,
and minReadySeconds at the above link).

The default "measurement of impact" here is that the updated copy does
not crash for `minReadySeconds`. This process can be customized further
with application specific logic via both liveness and readiness
probes. (The application configures these probes, and the deployment
controller will automatically factor them into the process.)

## Incremental updates with multiple deployments

If the impact of a change requires human judgments, or requires a long
time to measure, then it is still possible to leverage Kubernetes
primitives, but with a slightly different approach.

Kubernetes defines the concept of a deployment (a managed group of
servers) independently from the concept of what traffic is routed to
those deployments. This makes it possible to define multiple
deployments corresponding to two long-lived versions of our
application code, but have a single service routing traffic to all of
these deployments.

By controlling the replication count of each deployment independently,
it is also possible to control the proportion of traffic routed to
each version.

See
[here](https://kubernetes.io/docs/concepts/cluster-administration/manage-deployment/#canary-deployments
for details.

## How Forge can help with canaries

All the Forge example templates leverage the kubernetes builtin
deployment mechanism and so provide some level of canarying by
default. If more sophisticated behavior is required it is
straightforward to build templates that do something fancier, either
with the customization hooks using the single deployment scheme, or
via a multi-deployment template.
