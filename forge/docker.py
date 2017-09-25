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

import os, urllib2
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
        img = image(self.registry, self.namespace, name, version)
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
        return bool(sh("docker", "images", "-q", image(self.registry, self.namespace, name, version)).output)

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
        img = image(self.registry, self.namespace, name, version)
        sh("docker", "tag", source, img)

    @task()
    def push(self, name, version):
        self._login()
        img = image(self.registry, self.namespace, name, version)
        self.image_cache.pop(img, None)
        sh("docker", "push", img)
        return img

    @task("docker-build")
    def build(self, directory, dockerfile, name, version, args=None):
        args = args or {}

        buildargs = []
        for k, v in args.items():
            buildargs.append("--build-arg")
            buildargs.append("%s=%s" % (k, v))

        img = image(self.registry, self.namespace, name, version)

        sh("docker", "build", directory, "-f", dockerfile, "-t", img, *buildargs)
        return img

    @task()
    def validate(self):
        test_image = os.environ.get("FORGE_SETUP_IMAGE", "registry.hub.docker.com/datawire/forge-setup-test:1")
        self.pull(test_image)
        name, version = "forge_test", "dummy"
        self.tag(test_image, name, version)
        self.push(name, version)
        assert self.remote_exists(name, version)
