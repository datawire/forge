# Copyright 2017 datawire. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Forge CLI.
"""

from .tasks import (
    setup,
    task,
    TaskError
)

setup()

import click, os
from dotenv import find_dotenv, load_dotenv

import util
from . import __version__
from .core import Forge
from .kubernetes import Kubernetes
from collections import OrderedDict

ENV = find_dotenv(usecwd=True)
if ENV: load_dotenv(ENV)

@click.group()
@click.version_option(__version__, message="%(prog)s %(version)s")
@click.option('-v', '--verbose', count=True)
@click.option('--config', envvar='FORGE_CONFIG', type=click.Path(exists=True))
@click.option('--profile', envvar='FORGE_PROFILE')
@click.option('--branch', envvar='FORGE_BRANCH')
@click.option('--no-scan-base', is_flag=True)
@click.pass_context
def forge(context, verbose, config, profile, branch, no_scan_base):
    context.obj = Forge(verbose=verbose, config=config,
                        profile=None if profile is None else str(profile),
                        branch=None if branch is None else str(branch),
                        scan_base=not no_scan_base)

@forge.command()
@click.pass_obj
@click.argument('script', nargs=1, type=click.Path(exists=True))
@click.argument('args', nargs=-1)
@task()
def invoke(forge, script, args):
    """
    Invoke a python script using the forge runtime.

    Forge uses a portable self contained python runtime with a well
    defined set of packages in order to behave consistently across
    environments. The invoke command allows arbitrary python code to
    be executed using the forge runtime.


    The code is executed much as a normal python script, but with a
    few exceptions. The "forge" global variable is set to an instance
    of the forge object. Use forge.args to access any arguments
    supplied to the script.
    """
    forge.args = args
    execfile(script, {"forge": forge, "__file__": os.path.abspath(script)})

@forge.command()
@click.pass_obj
def setup(forge):
    """
    Help with first time setup of forge.

    Forge needs access to a container registry and a kubernetes
    cluster in order to deploy code. This command helps setup and
    validate the configuration necessary to access these resources.
    """
    return forge.setup()

@forge.group(invoke_without_command=True)
@click.pass_context
@click.option('-n', '--namespace', envvar='K8S_NAMESPACE', type=click.STRING)
@click.option('--dry-run', is_flag=True)
def build(ctx, namespace, dry_run):
    """Build deployment artifacts for a service.

    Deployment artifacts for a service consist of the docker
    containers and kubernetes manifests necessary to run your
    service. Forge automates the process of building your containers
    from source and producing the manifests necessary to run those
    newly built containers in kubernetes. Use `forge build
    [containers|manifests]` to build just containers, just manifests,
    or (the default) all of the above.

    How forge builds containers:

    By default every `Dockerfile` in your project is built and tagged
    with a version computed from the input sources. You can customize
    how containers are built using service.yaml. The `containers`
    property of `service.yaml` lets you specify an array.

    \b
    name: my-service
    ...
    container:
     - dockerfile: path/to/Dockerfile
       context: context/path
       args:
        MY_ARG: foo
        MY_OTHER_ARG: bar

    How forge builds deployment manifests:

    The source for your deployment manifests are kept as jinja
    templates in the k8s directory of your project. The final
    deployment templates are produced by rendering these templates
    with access to relevant service and build related metadata.

    You can use the `forge build metadata` command to view all the
    metadata available to these templates. See the `forge metadata`
    help for more info.

    """
    forge = ctx.obj
    forge.namespace = namespace
    forge.dry_run = dry_run
    if ctx.invoked_subcommand is None:
        forge.execute(forge.build)

@build.command()
@click.pass_obj
def metadata(forge):
    """
    Display build metadata.

    This command outputs all the build metadata available to manifests.
    """
    forge.metadata()

@build.command()
@click.pass_obj
def containers(forge):
    """
    Build containers for a service.

    See `forge build --help` for details on how containers are built.
    """
    forge.execute(forge.bake)

@build.command()
@click.pass_obj
def manifests(forge):
    """
    Build manifests for a service.

    See `forge build --help` for details on how manifests are built.
    """
    forge.execute(forge.manifest)

@forge.command()
@click.pass_obj
@click.option('-n', '--namespace', envvar='K8S_NAMESPACE', type=click.STRING)
@click.option('--dry-run', is_flag=True, help="Run through the deploy steps without making changes.")
@click.option('--prune', is_flag=True, help="Prune any resources not in the manifests.")
def deploy(forge, namespace, dry_run, prune):
    """
    Build and deploy a service.

    They deploy command performs a `forge build` and then applies the
    resulting deployment manifests using `kubectl apply`.
    """
    forge.namespace = namespace
    forge.dry_run = dry_run
    forge.execute(lambda svc: forge.deploy(*forge.build(svc), prune=prune))

@forge.command()
@click.pass_obj
def pull(forge):
    """
    Do a git pull on all services.
    """
    # XXX: should have a better way to track this, but this is quick
    pulled = {}
    forge.execute(lambda svc: forge.pull(svc, pulled))

@forge.command()
@click.pass_obj
def clean(forge):
    """
    Clean up intermediate containers used for building.
    """
    forge.execute(forge.clean)

@forge.group()
def schema_docs():
    """
    Generate schema documentation.
    """
    pass

@schema_docs.command()
def forge_yaml():
    """
    Output schema documentation for forge.yaml
    """
    import config
    config.CONFIG.render_all()

@schema_docs.command()
def service_yaml():
    """
    Output schema documentation for service.yaml
    """
    import service_info
    service_info.SERVICE.render_all()

def primary_version(resources):
    counts = OrderedDict()
    for r in resources:
        v = r["version"]
        if v not in counts:
            counts[v] = 0
        counts[v] += 1
    return sorted(counts.items(), cmp=lambda x, y: cmp(x[1], y[1]))[-1][0]

def unfurl(repos):
    for repo, services in sorted(repos.items()):
        for service, profiles in sorted(services.items()):
            for profile, resources in sorted(profiles.items()):
                yield repo, service, profile, resources

from fnmatch import fnmatch

def match(name, pattern):
    if not pattern:
        return True
    else:
        return fnmatch(name, pattern)

@forge.command()
@click.pass_obj
@click.argument("service_pattern", required=False)
@click.argument("profile_pattern", required=False)
@task()
def list(forge, service_pattern, profile_pattern):
    """
    List deployed forge services.

    The list command will query all k8s resources in all namespaces
    within a cluster and display a summary of useful information about
    those services. This includes the source repo where the service
    originates, the descriptor within the repo, and the status of any
    deployed k8s resources.

    You can use shell-style pattern matching for either the service or
    the profile in order to filter what is printed.
    """
    bold = forge.terminal.bold
    red = forge.terminal.bold_red

    kube = Kubernetes()
    repos = kube.list()
    first = True
    for repo, service, profile, resources in unfurl(repos):

        if not (match(service, service_pattern) and match(profile, profile_pattern)):
            continue

        descriptor = resources[0]["descriptor"]
        version = primary_version(resources)

        if first:
            first = False
        else:
            print

        header = "{0}[{1}]: {2} | {3} | {4}".format(bold(service), bold(profile), repo or "(none)", descriptor,
                                                     version)
        print header

        for resource in sorted(resources):
            ver = resource["version"]
            if ver != version:
                red_ver = red(ver)
                print "  {kind} {namespace}.{name} {0}:\n    {status}".format(red_ver, **resource)
            else:
                print "  {kind} {namespace}.{name}:\n    {status}".format(**resource)

@forge.command()
@click.pass_obj
@click.argument("service", required=False)
@click.argument("profile", required=False)
@click.option("--all", is_flag=True, help="Delete all services.")
@task()
def delete(forge, service, profile, all):
    """
    Delete (undeploy) k8s resources associated with a given profile or service.


    The delete command removes all forge deployed kubernetes
    resources for the specified service. If the profile is supplied
    then only the resources for that profile are removed. If the
    `--all` option is supplied then all forge deployed resources are
    removed from the entire cluster.

    """

    if all and (service or profile):
        raise TaskError("cannot specify an argument with the --all option")

    if not all and not service:
        raise TaskError("either supply a service or the --all option")

    labels = {
        "forge.service": service
    }

    kube = Kubernetes()

    if not all:
        repos = kube.list()
        services = set()
        profiles = set()
        for r, svc, prof, _ in unfurl(repos):
            services.add(svc)
            profiles.add((svc, prof))

        if service not in services:
            raise TaskError("service has no resources: %s" % service)

        if profile:
            if (service, profile) not in profiles:
                raise TaskError("profile has no resources: %s" % profile)

    if profile:
        labels["forge.profile"] = profile

    with task.verbose(True):
        kube.delete(labels)

def call_main():
    util.setup_yaml()
    try:
        exit(forge())
    except TaskError, e:
        exit(e)
    except KeyboardInterrupt, e:
        exit(e)

if __name__ == "__main__":
    call_main()
