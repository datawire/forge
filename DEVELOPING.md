# Forge

The dev.sh script provides a canonical testing and development
environment for forge using docker.

## Simple development:

Run `dev.sh shell` and you will get a development container with a
development installation (`pip install -e`) for forge.

You can hack on the source as much as you like, run forge, run some
tests (via `py.test -svv -k <test_name>`) and see the results.

## Running the full test suite:

Forge tests require interacting with a number of remote systems like
container registries and kubernetes clusters, so if you want to run
the full test suite you will need to set up some credentials for these
external systems:

1. Copy env.in to env and follow the directions listed in that file
   for obtaining a kubernaut token and for supplying AWS credentials.

Once you have done this, you can run `dev.sh test` and the full test
suite will run exactly as it does in CI.

## Bridged development:

If you are like me and you like to edit your source code outside the
container, then you might appreciate `dev.sh bridge`. This is very
similar to `dev.sh shell` however it additionally sets up a background
container to live sync the source code into the development container.

If you use this, please be aware that any changes to source code (or
git metadata) that you make from inside the dev container will be
overwritten by the files outside the container the next time you make
a change.

You can run `dev.sh clean` to remove the background container and
volume used to sync.
