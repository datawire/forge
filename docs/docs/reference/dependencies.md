# Service Dependencies

Kubernetes is great for *running* distributed applications composed of
many services, but *developing* this sort of application involves a
lot of tedium. Redeploying just a single service involves a number
steps:

 - docker build
 - pick a unique image tag
 - docker tag
 - docker push
 - (re)generate deployment yaml with new image tags
 - (re)apply deployment yaml

This gets even worse if your application contains many interdependent
services.

By specifying service level dependencies as part of your service.yaml,
forge will automatically figure out which applications need to be
(re)deployed, and then do this for you quickly and easily.

You can do this by specifying a `requires` property in your
`service.yaml`:

```
name: ratings   # the name of this service
requires:       # the name of any services necessary for this service to function
- users
- products
...
```

Now, when you deploy the ratings service, forge will automatically
search for the users and products services and (if necessary)
(re)deploy them also.

Forge looks for required services as follows:

1. your workspace is searched (the directory containing forge.yaml)
2. if forge is operating on a git checkout, forge will query the git
   server (based on the remote url for origin)

This allows natural usage of both a monorepo, as well as using a
single service per repo. If your application lives in one or more
monorepos, simply check it out in your workspace and forge will find
any dependent services.

## Startup Order

Forge does not attempt to guarantee any particular startup or
deployment order. This is because in general it is impossible to
guarantee startup order in distributed systems since any server may
fail/restart at any given time.

If you are writing a service that depends on other services, you
should expect your dependencies to become temporarily unavailable and
ensure that your service can recover when this happens. If you follow
this best practice, then your application will also be robust to
arbitrary startup orders.

**Still have questions? Ask in our [Gitter chatroom](https://gitter.im/datawire/forge) or [file an issue on GitHub](https://github.com/datawire/forge/issues/new).**