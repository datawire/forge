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

import base64, boto3, os, urllib2, hashlib
from tasks import task, TaskError, get, sh, Secret


class DockerImageBuilderError(Exception):

    report_traceback = False
    pass

class DockerImageBuilder(object):

    DOCKER = 'docker'
    IMAGEBUILDER = 'imagebuilder'

    @classmethod
    def get_cmd_from_name(self, str):
        if str == self.DOCKER:
            def docker_build(directory, dockerfile, img, buildargs):
                return ["docker", "build", directory, "-f", dockerfile, "-t", img] + buildargs
            return docker_build
        elif str == self.IMAGEBUILDER:
            def imagebuilder_build(directory, dockerfile, img, buildargs):
                return ["imagebuilder", "-f", dockerfile, "-t", img] + buildargs + [directory]
            return imagebuilder_build

        raise DockerImageBuilderError("No build method named %s exists. Available method names are: %s" % (str, ", ".join(methods)))

def image(registry, namespace, name, version):
    parts = (registry, namespace, "%s:%s" % (name, version))
    return "/".join(p for p in parts if p)

class DockerBase(object):

    def __init__(self):
        self.image_cache = {}
        self.logged_in = False

    def _login(self):
        if not self.logged_in:
            self._do_login()
            self.logged_in = True

    @task()
    def local_exists(self, name, version):
        return bool(sh("docker", "images", "-q", self.image(name, version)).output)

    @task()
    def exists(self, name, version):
        return self.remote_exists(name, version) or self.local_exists(name, version)

    @task()
    def needs_push(self, name, version):
        return self.local_exists(name, version) and not self.remote_exists(name, version)

    @task()
    def pull(self, image):
        self._login()
        sh("docker", "pull", image)

    @task()
    def tag(self, source, name, version):
        img = self.image(name, version)
        sh("docker", "tag", source, img)

    def _create_repo(self, name):
        pass

    @task()
    def push(self, name, version):
        self._login()
        self._create_repo(name)
        img = self.image(name, version)
        self.image_cache.pop(img, None)
        sh("docker", "push", img)
        return img

    @task()
    def build(self, directory, dockerfile, name, version, args, image_builder=None):
        args = args or {}

        image_builder = image_builder or DockerImageBuilder.DOCKER

        buildargs = []
        for k, v in args.items():
            buildargs.append("--build-arg")
            buildargs.append("%s=%s" % (k, v))

        img = self.image(name, version)

        cmd = DockerImageBuilder.get_cmd_from_name(image_builder)
        sh(*cmd(directory, dockerfile, img, buildargs))

        return img

    def get_changes(self, dockerfile):
        entrypoint = None
        cmd = None
        with open(dockerfile) as f:
            for line in f:
                parts = line.split()
                if parts and parts[0].lower() == "cmd":
                    cmd = line
                elif parts and parts[0].lower() == "entrypoint":
                    entrypoint = line
        return (entrypoint or 'ENTRYPOINT []', cmd or 'CMD []')

    def builder_hash(self, dockerfile, args):
        result = hashlib.sha1()
        with open(dockerfile) as fd:
            result.update(fd.read())
        result.update("--")
        for a in sorted(args.keys()):
            result.update(a)
            result.update("--")
            result.update(args[a])
            result.update("--")
        return result.hexdigest()

    def builder_prefix(self, name):
        return "forge_%s" % name

    def find_builders(self, name):
        builder_prefix = self.builder_prefix(name)
        containers = sh("docker", "ps", "-qaf", "name=%s" % builder_prefix, "--format", "{{.ID}} {{.Names}}")
        for line in containers.output.splitlines():
            id, builder_name = line.split()
            yield id, builder_name

    @task()
    def builder(self, directory, dockerfile, name, version, args, image_builder=None):
        # We hash the buildargs and Dockerfile so that we reconstruct
        # the builder container if anything changes. This might want
        # to be extended to cover other files the Dockerfile
        # references somehow at some point. (Maybe we could use the
        # spec stuff we use in .forgeignore?)
        builder_name = "%s_%s" % (self.builder_prefix(name), self.builder_hash(dockerfile, args))

        cid = None
        for id, bname in self.find_builders(name):
            if bname == builder_name:
                cid = id
            else:
                Builder(self, id).kill()
        if not cid:
            image = self.build(directory, dockerfile, name, version, args, image_builder=None)
            cid = sh("docker", "run", "--rm", "--name", builder_name, "-dit", "--entrypoint", "/bin/sh",
                     image).output.strip()
        return Builder(self, cid, self.get_changes(dockerfile))

    @task()
    def clean(self, name):
        for id, bname in self.find_builders(name):
            Builder(self, id).kill()

    @task()
    def validate(self, name="forge_test"):
        test_image = os.environ.get("FORGE_SETUP_IMAGE", "registry.hub.docker.com/datawire/forge-setup-test:1")
        self.pull(test_image)
        version = "dummy"
        self.tag(test_image, name, version)
        self.push(name, version)
        assert self.remote_exists(name, version)

    @task()
    def run(self, name, version, cmd, *args):
        return sh("docker", "run", "--rm", "-it", "--entrypoint", cmd, self.image(name, version), *args)


class Builder(object):

    def __init__(self, docker, cid, changes=()):
        self.docker = docker
        self.cid = cid
        self.changes = changes

    def run(self, *args):
        # XXX: for some reason when we put a -t here it messes up the
        # terminal output
        return sh("docker", "exec", "-i", self.cid, *args)

    def cp(self, source, target):
        return sh("docker", "cp", source, "{0}:{1}".format(self.cid, target))

    def commit(self, name, version):
        args = []
        for change in self.changes:
            args.append("-c")
            args.append(change)
        args.extend((self.cid, self.docker.image(name, version)))
        return sh("docker", "commit", *args)

    def kill(self):
        sh("docker", "kill", self.cid, expected=(0, 1))


class Docker(DockerBase):

    def __init__(self, registry, namespace, user, password):
        DockerBase.__init__(self)
        self.registry = registry
        self.namespace = namespace
        self.user = user
        self.password = password

    @task()
    def image(self, name, version):
        return image(self.registry, self.namespace, name, version)

    def _do_login(self):
        sh("docker", "login", "-u", self.user, "-p", Secret(self.password), self.registry)

    @task()
    def registry_get(self, api):
        url = "https://%s/v2/%s" % (self.registry, api)
        response = get(url, auth=(self.user, self.password),
                       headers={"Accept": 'application/vnd.docker.distribution.manifest.v2+json'})
        if response.status_code == 401:
            challenge = response.headers['Www-Authenticate']
            if challenge.startswith("Bearer "):
                challenge = challenge[7:]
            opts = urllib2.parse_keqv_list(urllib2.parse_http_list(challenge))
            authresp = get("{realm}?service={service}&scope={scope}".format(**opts), auth=(self.user, self.password))
            if authresp.ok:
                token = authresp.json()['token']
                response = get(url, headers={'Authorization': 'Bearer %s' % token})
            else:
                raise TaskError("problem authenticating with docker registry: [%s] %s" % (authresp.status_code,
                                                                                          authresp.content))
        return response

    @task()
    def repo_get(self, name, api):
        return self.registry_get("%s/%s/%s" % (self.namespace, name, api))

    @task()
    def remote_exists(self, name, version):
        img = self.image(name, version)
        if img in self.image_cache:
            return self.image_cache[img]

        response = self.repo_get(name, "manifests/%s" % version)
        result = response.json()
        # v1 and v2 manifest schemas look a bit different
        if 'fsLayers' in result or 'layers' in result:
            self.image_cache[img] = True
            return True
        elif 'errors' in result and result['errors']:
            if result['errors'][0]['code'] in ('MANIFEST_UNKNOWN', 'NAME_UNKNOWN'):
                self.image_cache[img] = False
                return False
        raise TaskError(response.content)

def _get_account():
    sts = boto3.client('sts')
    return sts.get_caller_identity()["Account"]

def _get_region():
    return boto3.Session().region_name

class ECRDocker(DockerBase):

    def __init__(self, account=None, region=None, aws_access_key_id=None, aws_secret_access_key=None):
        DockerBase.__init__(self)
        self.account = account or _get_account()
        self.region = region or _get_region()
        kwargs = {}
        if aws_access_key_id: kwargs['aws_access_key_id'] = aws_access_key_id
        if aws_secret_access_key: kwargs['aws_secret_access_key'] = aws_secret_access_key
        self.ecr = boto3.client('ecr', self.region, **kwargs)
        self.url = "{}.dkr.ecr.{}.amazonaws.com".format(self.account, self.region)

    @property
    def registry(self):
        return self.url

    @property
    def namespace(self):
        return None

    def _do_login(self):
        response = self.ecr.get_authorization_token(registryIds=[self.account])
        data = response['authorizationData'][0]
        token = data['authorizationToken']
        user, password = base64.decodestring(token).split(":")
        proxy = data['proxyEndpoint']
        sh("docker", "login", "-u", user, "-p", Secret(password), proxy)

    @task()
    def image(self, name, version):
        return "{}/{}:{}".format(self.url, name, version)
        #return image(self.registry, self.namespace, name, version)

    def _create_repo(self, name):
        try:
            self.ecr.create_repository(repositoryName=name)
            task.info('repository {} created'.format(name))
        except self.ecr.exceptions.RepositoryAlreadyExistsException, e:
            task.info('repository {} already exists'.format(name))

    @task()
    def remote_exists(self, name, version):
        try:
            task.info('checking for remote version: %r' % version)
            response =  self.ecr.describe_images(registryId=self.account,
                                                 repositoryName=name,
                                                 imageIds=[{'imageTag': version}])
            tags = set([t for id in response['imageDetails'] for t in id['imageTags']])
            return version in tags
        except self.ecr.exceptions.ImageNotFoundException, e:
            return False
        except self.ecr.exceptions.RepositoryNotFoundException, e:
            return False
