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

import pytest, yaml
from collections import OrderedDict
from forge.schema import Any, Scalar, Schema, Class, Field, String, Integer, Float, Sequence, Map, Union, Constant, \
    SchemaError, OMIT, Boolean
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
        Field("float", Float()),
        Field("bool", Boolean())
    )

    obj = {"string": "asdf", "integer": 3, "float": 3.14159, "bool": True}
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
              Class("foo", Klass, Field("type", Constant("c")), Field("foo", String())),
              Class("foobar", Klass, Field("type", Constant("d")), Field("foobar", String())))
    assert s.load("test", "asdf") == "asdf"
    assert s.load("test", "[a, b, c]") == ["a", "b", "c"]
    assert s.load("test", "type: a") == Klass(type="a", a=True)
    assert s.load("test", "type: b") == Klass(type="b", b=True)
    assert s.load("test", "type: c\nfoo: bar") == Klass(type="c", foo="bar")
    assert s.load("test", "type: d\nfoobar: bar") == Klass(type="d", foobar="bar")

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

def test_scalar():
    s = Scalar()
    assert s.load("test", "pi") == "pi"
    assert s.load("test", "3.14159") == 3.14159
    assert s.load("test", "3") == 3

SCALAR_VALIDATIONS = (
    (String, "1", "expecting string, got int"),
    (Integer, "a", "expecting integer, got string"),
    (Float, "a", "expecting one of (float|integer), got string"),
    (Boolean, "a", "expecting bool, got string")
)

@pytest.mark.parametrize("cls,input,error", SCALAR_VALIDATIONS)
def test_scalar_validation(cls, input, error):
    s = cls()
    try:
        s.load("test", input)
        assert False, "expecting error"
    except SchemaError, e:
        assert error in str(e)

def test_generic_class():
    s = Class("foo", "docs", Field("foo", String(), default=OMIT))
    obj = s.load("test", "foo: bar")
    assert obj == OrderedDict(foo="bar")
    assert isinstance(obj, OrderedDict)

def test_omit():
    s = Class("foo", "docs", Field("foo", String(), default=OMIT))
    assert s.load("test", "{}") == {}

def test_lax():
    s = Class("foo", "docs", Field("foo", String()), strict=False)
    assert s.load("test", "{foo: bar, baz: moo}") == OrderedDict(foo="bar", baz="moo")

AMBIGUOUS_UNIONS = (
    (lambda: Union(String(), String()),
     "ambiguous union: string appears multiple times"),
    (lambda: Union(Class("a", "a docs", Field("type", Constant("a"))),
                   Class("b", "b docs", Field("type", Constant("a")))),
     "ambiguous union: a:map{type=a}, b:map{type=a}"),
    (lambda: Union(Class("a", "a docs", Field("type", Constant("a"))),
                   Class("b", "b docs", Field("type", String()))),
     "ambiguous union: a:map{type=a}, b:map"),
    (lambda: Union(Class("a", "a docs", Field("type", Constant("a"))),
                   Class("b", "b docs", Field("c", Constant("x")), Field("type", String()))),
     "ambiguous union: 'type' both constant and unconstrained"),
    (lambda: Union(Class("a", "a docs", Field("type", Constant("a"))), Map(Any())),
     "ambiguous union: map and a:map{type=a}")
)

@pytest.mark.parametrize("input,error", AMBIGUOUS_UNIONS)
def test_ambiguous_union(input, error):
    try:
        input()
        assert False, "expected error: %s" % error
    except ValueError, e:
        assert error in str(e), e

ABC = Union(String(),
            Class("a", "a docs", Field("type", Constant("a")), Field("a", String())),
            Class("b", "b docs", Field("type", Constant("b")), Field("b", String())),
            Class("c", "c docs", Field("type", Constant("c")), Field("c", String())))

ABC_FIELDS = Union(Class("a", "a docs", Field("a", Constant("x")), Field("aa", String())),
                   Class("b", "b docs", Field("b", Constant("x")), Field("bb", String())),
                   Class("c", "c docs", Field("c", Constant("x")), Field("cc", String())))

ABC_STR_CONSTANTS = Union(Integer(),
                          Float(),
                          Boolean(),
                          Class("a", "a docs", Field("a", Constant("y"))),
                          Constant("b"),
                          Constant("c"))

UNION_ERRORS = (
    (ABC, "[]", "expecting one of (string|a:map{type=a}|b:map{type=b}|c:map{type=c}"),
    (ABC, "{type: a, b: blah}", "no such field: b"),
    (ABC, "{type: b, b: []}", "expecting string, got sequence"),
    (ABC, "{}", "expecting one of (a:map{type=a}|b:map{type=b}|c:map{type=c})"),
    (ABC_FIELDS, "[]", "expecting one of (a:map{a=x}|b:map{b=x}|c:map{c=x})"),
    (ABC_FIELDS, "{a: x}", "required field 'aa' is missing"),
    (ABC_FIELDS, "{b: x}", "required field 'bb' is missing"),
    (ABC_FIELDS, "{c: x}", "required field 'cc' is missing"),
    (ABC_FIELDS, "{}", "expecting one of (a:map{a=x}|b:map{b=x}|c:map{c=x})"),
    (ABC_FIELDS, "{a: []}", "expecting one of (a:map{a=x}|b:map{b=x}|c:map{c=x})"),
    (ABC_FIELDS, "{a: {}}", "expecting one of (a:map{a=x}|b:map{b=x}|c:map{c=x})"),
    (ABC_STR_CONSTANTS, "{}", "required field 'a' is missing"),
    (ABC_STR_CONSTANTS, "a", "expecting one of (integer|b|float|bool|c|a:map{a=y}), got string(a)"),
    (Union(String(), Sequence(String())), "foo: bar", "expecting one of (string|sequence), got map")
)

@pytest.mark.parametrize("schema,input,error", UNION_ERRORS)
def test_union_error(schema, input, error):
    try:
        schema.load("test", input)
        assert False, "expected error: %s" % error
    except SchemaError, e:
        assert error in str(e)
