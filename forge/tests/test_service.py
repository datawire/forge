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

import os, pytest
from forge.core import Forge
from forge.service import load_service_yamls, Discovery
from forge.tasks import sh, TaskError
from .common import mktree

def ERROR(message, content):
    return (message, content)
def VALID(content):
    return (None, content)

YAML = (
# unlexable
    ERROR("error parsing service yaml:", "name: *"),
# unparseable
    ERROR("error parsing service yaml:", "{"),
# root
    ERROR("expected a single yaml document, found 0 documents", ""),
    ERROR("required field 'name' is missing", "{}"),
    VALID("name: foo"),
# name
    ERROR("expecting string, got int", "name: 3"),
    ERROR("expecting string, got bool", "name: true"),
    ERROR("expecting string, got map", "name: {}"),
# requires
    ERROR("expecting one of (string|sequence), got int",
          """
name: foo
requires: 3
          """),
    ERROR("expecting one of (string|sequence), got map",
          """
name: foo
requires:
  foo: bar
          """),
    ERROR("expecting string, got int",
          """
name: foo
requires:
 - 3
     """),
    VALID("""
name: foo
requires: asdf
    """),
    VALID("""
name: foo
requires:
 - asdf
 - fdsa
    """),
# containers
    ERROR("expecting sequence[(string|container)], got string",
     """
name: foo
containers: blah
     """),
    ERROR("expecting one of (string|container:map), got int",
     """
name: foo
containers: [1, 2, 3]
     """),
# containers.item
    ERROR("no such field: a",
     """
name: foo
containers:
- a: b
     """),
    VALID("""
name: foo,
containers:
 - foo
    """),
    VALID("""
name: foo,
containers:
 - dockerfile: bar
   context: .
   args:
     foo: bar
    """),
# istio
    VALID("""
name: foo,
istio:
 enabled: false
    """),
    VALID("""
name: foo,
istio:
 enabled: true
 includeIPRanges:
  - 10.0.0.0/8
  - 172.32.0.0/16
    """)
)

@pytest.mark.parametrize("error,content", YAML)
def test_service_yaml(error, content):
    try:
        load_service_yamls("test", content)
        if error is not None:
            assert False, "expected error: %s" % error
    except TaskError, err:
        if error is None:
            raise
        else:
            assert error in str(err)

GIT_ROOT = r"""
@@.gitignore
*.pyc
@@
"""

ROOT_SVC = r"""
@@.forgeignore
*.rootignore
@@

@@service.yaml
name: root
@@

@@Dockerfile
@@

@@root.py
@@

@@root.pyc
@@

@@blah.rootignore
@@

@@subdir/Dockerfile
@@

@@subdir/app.py
@@

@@subdir/app.pyc
@@
"""

NESTED_SVC = r"""
@@nested/service.yaml
name: nested
@@

@@nested/Dockerfile
@@

@@nested/nested.py
@@

@@nested/nested.pyc
@@

@@nested/.gitignore
workdir
@@

@@nested/.forgeignore
*.nestedignore
@@

@@nested/workdir/stuff
@@

@@nested/blah.rootignore
@@

@@nested/blah.nestedignore
@@
"""

def mkgittree(treespec, **substitutions):
    directory = mktree(treespec, **substitutions)
    sh("git", "init", ".", cwd=directory)
    sh("git", "add", ".", cwd=directory)
    sh("git", "commit", "-m", "initial commit", cwd=directory)
    return directory

def test_discovery_root():
    directory = mkgittree(GIT_ROOT + ROOT_SVC)
    disco = Discovery(Forge())
    found = disco.search(directory)
    assert [f.name for f in found] == ["root"]

    svc = disco.services["root"]
    assert set(svc.dockerfiles) == set(["Dockerfile", "subdir/Dockerfile"])
    assert set(svc.files) == set([".gitignore",
                                  ".forgeignore",
                                  "service.yaml",
                                  "Dockerfile",
                                  "root.py",
                                  "subdir/Dockerfile",
                                  "subdir/app.py"])

def test_discovery_nested():
    directory = mkgittree(GIT_ROOT + NESTED_SVC)
    disco = Discovery(Forge())
    found = disco.search(directory)
    assert [f.name for f in found] == ["nested"]

    svc = disco.services["nested"]
    assert set(svc.dockerfiles) == set(["Dockerfile"])
    assert set(svc.files) == set([".gitignore",
                                  ".forgeignore",
                                  "service.yaml",
                                  "Dockerfile",
                                  "nested.py",
                                  "service.yaml",
                                  "blah.rootignore"])

def test_discovery_combined():
    directory = mkgittree(GIT_ROOT + ROOT_SVC + NESTED_SVC)
    disco = Discovery(Forge())
    found = disco.search(directory)
    assert [f.name for f in found] == ["root", "nested"]

    root = disco.services["root"]
    assert set(root.dockerfiles) == set(["Dockerfile", "subdir/Dockerfile"])
    assert set(root.files) == set([".gitignore",
                                   ".forgeignore",
                                   "service.yaml",
                                   "Dockerfile",
                                   "root.py",
                                   "subdir/Dockerfile",
                                   "subdir/app.py"])

    nested = disco.services["nested"]
    assert set(nested.dockerfiles) == set(["Dockerfile"])
    assert set(nested.files) == set([".gitignore",
                                     ".forgeignore",
                                     "service.yaml",
                                     "Dockerfile",
                                     "nested.py",
                                     "service.yaml"])

    assert root.version == nested.version

def test_versioning():
    directory = mkgittree(GIT_ROOT + ROOT_SVC)

    v1 = Discovery(Forge()).search(directory)[0].version
    assert v1.endswith(".git")

    with open(os.path.join(directory, "root.py"), "write") as fd:
        fd.write("blah")
    v2 = Discovery(Forge()).search(directory)[0].version
    assert v2.endswith(".sha")

    with open(os.path.join(directory, "root.py"), "write") as fd:
        fd.write("blahblah")
    v3 = Discovery(Forge()).search(directory)[0].version

    assert v3.endswith(".sha")
    assert v2 != v3

def test_nonexistent():
    try:
        Discovery(Forge()).search("thisfileshouldreallynotexist")
    except TaskError, e:
        assert "no such directory" in str(e)

def test_nondirectory():
    try:
        Discovery(Forge()).search(__file__)
    except TaskError, e:
        assert "not a directory" in str(e)
