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

import os, urllib2, hashlib
from tasks import task, TaskError, get, sh, Secret

def image(registry, namespace, name, version):
    return "%s/%s/%s:%s" % (registry, namespace, name, version)

class Docker(object):

    def __init__(self, registry, namespace, user, password):
        self.registry = registry
        self.namespace = namespace
        self.user = user
        self.password = password
        self.image_cache = {}
        self.logged_in = False

    @task()
    def image(self, name, version):
        return image(self.registry, self.namespace, name, version)

    def _login(self):
        if not self.logged_in:
            sh("docker", "login", "-u", self.user, "-p", Secret(self.password), self.registry)
            self.logged_in = True

    @task()
    def registry_get(self, api):
        url = "https://%s/v2/%s" % (self.registry, api)
        response = get(url, auth=(self.user, self.password))
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
        if 'signatures' in result and 'fsLayers' in result:
            self.image_cache[img] = True
            return True
        elif 'errors' in result and result['errors']:
            if result['errors'][0]['code'] == 'MANIFEST_UNKNOWN':
                self.image_cache[img] = False
                return False
        raise TaskError(response.content)

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

    @task()
    def push(self, name, version):
        self._login()
        img = self.image(name, version)
        self.image_cache.pop(img, None)
        sh("docker", "push", img)
        return img

    @task()
    def build(self, directory, dockerfile, name, version, args):
        args = args or {}

        buildargs = []
        for k, v in args.items():
            buildargs.append("--build-arg")
            buildargs.append("%s=%s" % (k, v))

        img = self.image(name, version)

        sh("docker", "build", directory, "-f", dockerfile, "-t", img, *buildargs)
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
    def builder(self, directory, dockerfile, name, version, args):
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
            image = self.build(directory, dockerfile, name, version, args)
            cid = sh("docker", "run", "--rm", "--name", builder_name, "-dit", "--entrypoint", "/bin/sh",
                     image).output.strip()
        return Builder(self, cid, self.get_changes(dockerfile))

    @task()
    def clean(self, name):
        for id, bname in self.find_builders(name):
            Builder(self, id).kill()

    @task()
    def validate(self):
        test_image = os.environ.get("FORGE_SETUP_IMAGE", "registry.hub.docker.com/datawire/forge-setup-test:1")
        self.pull(test_image)
        name, version = "forge_test", "dummy"
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
        return sh("docker", "exec", "-it", self.cid, *args)

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
