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

import pytest
from forge.service import load_service_yamls
from forge.tasks import TaskError

def ERROR(message, content):
    return (message, content)
def VALID(content):
    return (None, content)

YAML = (
# root
    ERROR("None is not of type 'object'", ""),
    ERROR("'name' is a required property", "{}"),
    VALID("name: foo"),
# name
    ERROR("3 is not of type 'string'", "name: 3"),
    ERROR("True is not of type 'string'", "name: true"),
    ERROR("{} is not of type 'string'", "name: {}"),
# requires
    ERROR("3 is not of type 'string'",
          """
name: foo
requires: 3
          """),
    ERROR("{'foo': 'bar'} is not of type 'string'",
          """
name: foo
requires:
  foo: bar
          """),
    ERROR("[3] is not of type 'string'",
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
    ERROR("'blah' is not of type 'array'",
     """
name: foo
containers: blah
     """),
    ERROR("1 is not of type 'string'",
     """
name: foo
containers: [1, 2, 3]
     """),
# containers.item
    ERROR("{'a': 'b'} is not of type 'string'",
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
