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

import yaml
from collections import OrderedDict
from forge.schema import Schema, Class, Field, String, Integer, Float, Sequence, Map, SchemaError
from forge import util

class Klass(object):

    def __init__(self, **fields):
        self.fields = fields

    def __eq__(self, other):
        return self.fields == other.fields

def test_scalars():
    s = Class(
        Klass,
        Field("string", String()),
        Field("integer", Integer()),
        Field("float", Float())
    )

    obj = {"string": "asdf", "integer": 3, "float": 3.14159}
    k1 = s.load("test", yaml.dump(obj))
    k2 = Klass(**obj)
    assert k1 == k2

def test_unknown_field():
    s = Class(
        Klass,
        Field("foo", String())
    )

    obj = {"foo": "asdf", "bar": "fdsa"}
    try:
        s.load("test", yaml.dump(obj))
        assert False, "should have errored"
    except SchemaError, e:
        assert "no such field: bar" in str(e)

def test_alias():
    s = Class(Klass, Field("foo-bar", String(), "foo_bar"))
    k = s.load("test", "{foo-bar: foobar}")
    assert k.fields == {"foo_bar": "foobar"}

def test_sequence():
    s = Sequence(String())
    assert s.load("test", "[a, b, c]") == ["a", "b", "c"]

def test_map():
    s = Map(String())
    assert s.load("test", "{a: b, c: d}") == {"a": "b", "c": "d"}
