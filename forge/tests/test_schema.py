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
from forge.schema import Any, Schema, Class, Field, String, Integer, Float, Sequence, Map, Union, Constant, SchemaError
from forge import util

class Klass(object):

    def __init__(self, **fields):
        self.fields = fields

    def __eq__(self, other):
        return self.fields == other.fields

def test_scalars():
    s = Class(
        "scalars",
        Klass,
        Field("string", String()),
        Field("integer", Integer()),
        Field("float", Float())
    )

    obj = {"string": "asdf", "integer": 3, "float": 3.14159}
    k1 = s.load("test", yaml.dump(obj))
    k2 = Klass(**obj)
    assert k1 == k2

def test_null():
    for s in (String(), Integer(), Float(), Constant("asdf")):
        assert s.load("test", "null") == None

def test_unknown_field():
    s = Class(
        "foo",
        Klass,
        Field("foo", String())
    )

    obj = {"foo": "asdf", "bar": "fdsa"}
    try:
        s.load("test", yaml.dump(obj))
        assert False, "should have errored"
    except SchemaError, e:
        assert "no such field: bar" in str(e)

def test_missing_field():
    s = Class(
        "foo",
        Klass,
        Field("foo", String()),
        Field("bar", String())
    )

    obj = {"bar": "asdf"}
    try:
        s.load("test", yaml.dump(obj))
    except SchemaError, e:
        assert "required field 'foo' is missing" in str(e)

def test_default_field():
    s = Class(
        "foo",
        Klass,
        Field("foo", String(), default=None),
        Field("bar", String(), default="asdf")
    )

    k = s.load("test", "{}")
    assert k == Klass(foo=None, bar="asdf")

def test_alias():
    s = Class("foobar", Klass, Field("foo-bar", String(), "foo_bar"))
    k = s.load("test", "{foo-bar: foobar}")
    assert k.fields == {"foo_bar": "foobar"}

def test_sequence():
    s = Sequence(String())
    assert s.load("test", "[a, b, c]") == ["a", "b", "c"]

def test_map():
    s = Map(String())
    assert s.load("test", "{a: b, c: d}") == {"a": "b", "c": "d"}

def test_union():
    s = Union(String(),
              Sequence(String()),
              Class("type-a", lambda **kw: Klass(a=True, **kw), Field("type", Constant("a"))),
              Class("type-b", lambda **kw: Klass(b=True, **kw), Field("type", Constant("b"))),
              Class("foo", Klass, Field("foo", String())),
              Class("foobar", Klass, Field("foobar", String())),
              Map(String()))
    assert s.load("test", "asdf") == "asdf"
    assert s.load("test", "[a, b, c]") == ["a", "b", "c"]
    assert s.load("test", "type: a") == Klass(type="a", a=True)
    assert s.load("test", "type: b") == Klass(type="b", b=True)
    assert s.load("test", "foo: bar") == Klass(foo="bar")
    assert s.load("test", "foobar: bar") == Klass(foobar="bar")
    assert s.load("test", "bar: foo") == {"bar": "foo"}

def test_any():
    s = Any()
    assert s.load("test", "asdf") == "asdf"
    assert s.load("test", "[]") == []
    assert s.load("test", "[1, 2, 3]") == [1, 2, 3]
    assert s.load("test", "[a, b, c]") == ['a', 'b', 'c']
    assert s.load("test", "[1, two, 3.0, {four: five, 6.0: 7, ate: 8.0}]") == [1, 'two', 3.0,
                                                                               {"four": "five",
                                                                                "6.0": 7,
                                                                                "ate": 8.0}]
    assert s.load("test", "{a: b, c: 1, d: 1.0, e: [1, 2, 3]}") == {"a": "b",
                                                                    "c": 1,
                                                                    "d": 1.0,
                                                                    "e": [1, 2, 3]}
