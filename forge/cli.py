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
    cull,
    get,
    project,
    setup,
    sh,
    task,
    ERROR,
    Elidable,
    Secret,
    TaskError
)

setup()

import getpass

import click, base64, fnmatch, requests, os, sys, yaml
from dotenv import find_dotenv, load_dotenv
from collections import OrderedDict

import config, util
from . import __version__
from .service import Discovery, Service
from .docker import Docker, ECRDocker
from .kubernetes import Kubernetes
from .jinja2 import renders
from .istio import istio
from .output import Terminal
from scout import Scout

ENV = find_dotenv(usecwd=True)
if ENV: load_dotenv(ENV)

class CLIError(Exception): pass

SETUP_TEMPLATE = """# Global forge configuration
# DO NOT CHECK INTO GITHUB, THIS FILE CONTAINS SECRETS
{{yaml}}
"""

def file_contents(path):
    try:
        with open(os.path.expanduser(os.path.expandvars(path)), "read") as fd:
            return fd.read()
    except IOError, e:
        print "  %s" % e
        return None

class Forge(object):

    def __init__(self, verbose=0, config=None, profile=None, branch=None):
        self.verbose = verbose
        self.config = config or util.search_parents("forge.yaml")
        self.profile = profile
        self.namespace = None
        self.dry_run = False
        self.terminal = Terminal()
        self.discovery = Discovery(profile=profile, branch=branch)

        self.baked = []
        self.pushed = []
        self.rendered = []
        self.deployed = []

    def prompt(self, msg, default=None, loader=None, echo=True, optional=False):
        if optional:
            msg += ' (use "-" to leave unspecified)'
        prompt = "%s: " % msg if default is None else "%s[%s]: " % (msg, default)
        prompter = raw_input if echo else lambda: getpass.getpass("")

        while True:
            task.echo(prompt, newline=False)
            sys.stdout.flush()
            value = prompter() or default
            if value is None: continue
            if value == "-" and optional:
                value = None
            if loader is not None:
                loaded = loader(value)
                if loaded is None:
                    continue
            if loader:
                return value, loaded
            else:
                return value

    @task(context="setup")
    def setup(self):
        with task.verbose(True):
            scout = Scout("forge", __version__)
            scout_res = scout.report()

            task.echo(self.terminal.bold("== Checking Kubernetes Setup =="))
            task.echo()

            checks = (("kubectl", "version", "--short"),
                      ("kubectl", "get", "service", "kubernetes", "--namespace", "default"))

            for cmd in checks:
                e = sh.run(*cmd)
                if e.result is ERROR:
                    task.echo()
                    task.echo(self.terminal.bold_red("== Kubernetes Check Failed =="))
                    task.echo()
                    task.echo()
                    task.echo(self.terminal.bold("Please make sure kubectl is installed/configured correctly."))
                    raise CLIError("")

            regtype = "generic"
            prompts = {
                ("generic", "url"): ("Docker registry url", "registry.hub.docker.com"),
                ("generic", "user"): ("Docker user", None),
                ("generic", "namespace"): ("Docker namespace/organization", None),
                ("generic", "password"): ("Docker password", None),
                ("gcr", "key"): ["Path to json key", None]
            }

            @task()
            def validate():
                c = yaml.dump({"registry": regvalues})
                task.echo(c)
                conf = config.load("setup", c)
                dr = get_docker(conf.registry)
                dr.validate()

            task.echo()
            task.echo(self.terminal.bold("== Setting up Docker =="))

            while True:
                task.echo()
                types = OrderedDict((("ecr", config.ECR),
                                     ("gcr", config.GCR),
                                     ("generic", config.DOCKER)))
                regtype = self.prompt("Registry type (one of %s)" % ", ".join(types.keys()), regtype)
                if regtype not in types:
                    task.echo()
                    task.echo(
                        self.terminal.red("%s is not a valid choice, please choose one of %s" %
                                          (regtype, ", ".join(types.keys())))
                    )
                    task.echo()
                    regtype = "generic"
                    continue

                reg = types[regtype]
                regvalues = OrderedDict((("type", reg.fields["type"].type.value),))
                for f in reg.fields.values():
                    if f.name == "type": continue
                    prompt, default = prompts.get((regtype, f.name), (f.name, None))
                    if (regtype, f.name) == ("gcr", "key"):
                        key, value = self.prompt(prompt, default, loader=file_contents)
                        prompts[(regtype, f.name)][1] = key
                    else:
                        if f.name in ("password",):
                            value = self.prompt(prompt, default, echo=False)
                        else:
                            value = self.prompt(prompt, default, optional=not f.required)
                    if f.name in ("password", "key"):
                        regvalues[f.name] = base64.encodestring(value)
                    else:
                        regvalues[f.name] = value

                task.echo()
                e = validate.run()
                if e.result is ERROR:
                    task.echo()
                    task.echo(self.terminal.red("-- please try again --"))
                    e.recover()
                    continue
                else:
                    break

            task.echo()

            config_content = renders("SETUP_TEMPLATE", SETUP_TEMPLATE,
                                     yaml=yaml.dump({"registry": regvalues}, allow_unicode=True,
                                                    default_flow_style=False))

            config_file = "forge.yaml"

            task.echo(self.terminal.bold("== Writing config to %s ==" % config_file))

            with open(config_file, "write") as fd:
                fd.write(config_content)

            task.echo()
            task.echo(config_content.strip())
            task.echo()

            task.echo(self.terminal.bold("== Done =="))

    @task()
    def scan(self, directory):
        found = self.discovery.search(directory)
        return [f.name for f in found]

    @task()
    def bake(self, service):
        raw = list(cull(lambda c: not self.docker.exists(c.image, c.version), service.containers))
        baked = []

        for container in raw:
            ctx = service.name if len(raw) == 1 else "%s[%s]" % (service.name, (container.index + 1))
            with task.context(ctx), task.verbose(True):
                container.build.go(self)
            baked.append(container)

        task.sync()
        self.baked.extend(baked)

    @task()
    def push(self, service):
        unpushed = list(cull(lambda c: self.docker.needs_push(c.image, c.version), service.containers))

        pushed = []
        for container in unpushed:
            with task.verbose(True):
                pushed.append((container, self.docker.push(container.image, container.version)))

        task.sync()
        self.pushed.extend(pushed)

    def template(self, svc):
        k8s_dir = os.path.join(svc.root, ".forge", "k8s", svc.name)
        svc.deployment(self.docker.registry, self.docker.namespace, k8s_dir)
        return k8s_dir, self.kube.resources(k8s_dir)

    @task()
    def manifest(self, service):
        k8s_dir, resources = self.template(service)
        istioify = service.info().get("istio", False)
        if istioify:
            istio(k8s_dir)
        task.sync()
        self.rendered.append((service, k8s_dir, resources))
        return k8s_dir

    @task()
    def build(self, service):
        self.bake(service)
        self.push(service)
        return service, self.manifest(service)

    @task()
    def deploy(self, service, k8s_dir):
        self.kube.apply(k8s_dir)
        task.sync()
        self.deployed.append((service, k8s_dir))

    @task()
    def pull(self, service):
        with task.verbose(True):
            service.pull()

    def load_config(self):
        if not self.config:
            raise CLIError("unable to find forge.yaml, try running `forge setup`")

        try:
            conf = config.load(self.config)
        except config.SchemaError, e:
            raise CLIError(str(e))

        self.base = os.path.dirname(os.path.abspath(self.config))
        self.docker = get_docker(conf.registry)

        self.kube = Kubernetes(namespace=self.namespace, dry_run=self.dry_run)

    def load_services(self):
        start = util.search_parents("service.yaml")
        if start:
            path = os.path.dirname(start)
        else:
            path = os.getcwd()
        services = self.scan(path)
        if not os.path.samefile(path, self.base):
            self.scan(self.base)
        if services:
            services.extend(self.discovery.dependencies(services))
        return services

    @task()
    def metadata(self):
        self.load_config()
        services = self.load_services()
        if not services:
            raise TaskError("no service found")
        else:
            svc = self.discovery.services[services[0]]
            print yaml.dump(svc.metadata(self.docker.registry, self.docker.namespace))

    @task()
    def clean(self, service):
        with task.verbose(True):
            for container in service.containers:
                self.docker.clean(container.image)

    def execute(self, goal):
        self.load_config()

        @task(context="{0}")
        def service(name):
            svc = self.discovery.services[name]
            goal(svc)

        @task(context="forge")
        def root():
            with task.verbose(self.verbose):
                task.info("CONFIG: %s" % self.config)
                for name in self.load_services():
                    service.go(name)

        exe = root.run()
        if exe.result is ERROR:
            raise SystemExit(1)
        else:
            self.summary()

    @task(context="forge")
    def summary(self):
        task.echo()
        color = self.terminal.bold
        if self.baked:
            task.echo(color("   built: ") + ", ".join(os.path.relpath(c.abs_dockerfile) for c in self.baked))
        if self.pushed:
            task.echo(color("  pushed: ") + ", ".join("%s:%s" % (c.image, c.version) for (c, i) in self.pushed))
        if self.rendered:
            resources = []
            for s, k, r in self.rendered:
                resources.extend(r)
            task.echo(color("rendered: ") + (", ".join(resources) or "(none)"))
        if self.deployed:
            task.echo(color("deployed: ") + ", ".join(s.name for s, k in self.deployed))

def get_docker(registry):
    if registry.type == "ecr":
        return ECRDocker(
            account=registry.account,
            region=registry.region,
            aws_access_key_id=registry.aws_access_key_id,
            aws_secret_access_key=registry.aws_secret_access_key
        )
    elif registry.type == "gcr":
        return Docker(
            registry=registry.url,
            namespace=registry.project,
            user="_json_key",
            password=registry.key
        )
    else:
        return Docker(
            registry=registry.url,
            namespace=registry.namespace,
            user=registry.user,
            password=registry.password
        )

@click.group()
@click.version_option(__version__, message="%(prog)s %(version)s")
@click.option('-v', '--verbose', count=True)
@click.option('--config', envvar='FORGE_CONFIG', type=click.Path(exists=True))
@click.option('--profile', envvar='FORGE_PROFILE')
@click.option('--branch', envvar='FORGE_BRANCH')
@click.pass_context
def forge(context, verbose, config, profile, branch):
    context.obj = Forge(verbose=verbose, config=config,
                        profile=None if profile is None else str(profile),
                        branch=None if branch is None else str(branch))

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
@click.option('--dry-run', is_flag=True)
def deploy(forge, namespace, dry_run):
    """
    Build and deploy a service.

    They deploy command performs a `forge build` and then applies the
    resulting deployment manifests using `kubectl apply`.
    """
    forge.namespace = namespace
    forge.dry_run = dry_run
    forge.execute(lambda svc: forge.deploy(*forge.build(svc)))

@forge.command()
@click.pass_obj
def pull(forge):
    """
    Do a git pull on all services.
    """
    forge.execute(forge.pull)

@forge.command()
@click.pass_obj
def clean(forge):
    """
    Clean up intermediate containers used for building.
    """
    forge.execute(forge.clean)

def call_main():
    util.setup_yaml()
    try:
        exit(forge())
    except CLIError, e:
        exit(e)
    except KeyboardInterrupt, e:
        exit(e)

if __name__ == "__main__":
    call_main()
