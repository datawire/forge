# Forge

The forge command line tool depends on a functioning docker and
kubectl. You will also need istioctl in order to test the istio
integration.

PLEASE NOTE: Make sure that kubectl is pointed at a disposable
kubernetes cluster when you hack on forge since running the tests will
perform deployments into your cluster.

## Setting up a dev environment:

1. `git clone` this repository then change directory into it.

2. Make a Python2 virtualenv with `make virtualenv`

3. From your virtualenv run `pip install -e .`

4. Hack away...

## Running tests:

You can run tests by running `py.test` from your repo. As noted above,
the tests will perform kubectl apply operations against your cluster,
so make sure kubectl is pointed at a cluster where this is ok to
do. An easy way to do this is to point it at minikube.
