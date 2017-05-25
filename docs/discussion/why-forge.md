---
layout: doc
weight: 1
title: "Why Forge?"
categories: discussion
---

Kubernetes provides the powerful primitive of infrastructure as
configuration. It gives you a language that lets you describe the
infrastructure requirements needed for something to run, and then
keeps it running in the face of failures.
Forge makes it easy to leverage these capabilities when your code and
its requirements are quickly changing.

### For Operations
Forge can help operations quickly and easily set up a robust
deployment pipeline suitable for microservices. More often than not,
when starting from a monolithic pipeline, the mechanics performed by
forge end up being hardcoded into a bunch of scripts running from
jenkins (or similar). This makes it difficult to scale that pipeline
to work with many services across multiple environments.

Forge captures all the mechanics necessary to continuously deploy an
entire network of frequently updating services all the way from source
to a running Kubernetes cluster. This makes it trivial to set up
isolated dev environments, load testing, staging, integration
environments, as well as multiple production environments in a
consistent way.

### For Developers
Forge can help developers leverage the benefits of kubernetes quickly
and easily. Forge gets you shipping code on day one and lets you learn
the powerful stuff as/when needed.

The deployment templates allow you to capture and easily reuse useful
infrastructure level abstractions (e.g. my service uses redis), but
also allow you to customize and tune as needed for each individual
service. You get the guardrails without the straightjacket.

### For Organizations
Forge can help an organization scale.

For an organization to scale you need cross-functional independent
teams, but at the same time you want to be able to share best
practices and avoid duplicate work.

Forge's service templates capture best practices from both operations
and development, and help share knowledge/work between independent
teams.
