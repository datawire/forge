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

from forge.match import match, many
from forge.yamlutil import *

def test_map_view_getitem():
    v = view(compose("foo: bar"))
    assert v["foo"] == "bar"

def test_map_view_setitem_string():
    v = view(compose("{}"))
    v["foo"] = "bar"
    assert serialize(as_node(v)) == "{foo: bar}\n"

def test_map_view_setitem_int():
    v = view(compose("{}"))
    v["foo"] = 3
    assert serialize(as_node(v)) == "{foo: 3}\n"

def test_map_view_setitem_float():
    v = view(compose("{}"))
    v["foo"] = 3.14159
    assert serialize(as_node(v)) == "{foo: 3.14159}\n"

def test_map_view_setitem_none():
    v = view(compose("{}"))
    v["foo"] = None
    assert serialize(as_node(v)) == "{foo: null}\n"

def test_sequence_view_getitem():
    v = view(compose("[item]"))
    assert v[0] == "item"

def test_sequence_view_setitem_string():
    v = view(compose("[dummy]"))
    v[0] = "item"
    assert serialize(as_node(v)) == "[item]\n"

def test_sequence_view_setitem_int():
    v = view(compose("[dummy]"))
    v[0] = 3
    assert serialize(as_node(v)) == "[3]\n"

def test_sequence_view_setitem_float():
    v = view(compose("[dummy]"))
    v[0] = 3.14159
    assert serialize(as_node(v)) == "[3.14159]\n"

def test_sequence_view_setitem_none():
    v = view(compose("[dummy]"))
    v[0] = None
    assert serialize(as_node(v)) == "[null]\n"

def test_sequence_view_append():
    v = view(compose("[]"))
    v.append("item")
    assert v[0] == "item"

def test_traversal():
    expected = [("map", None), ("str", "key"), ("str", "value"), ("str", "list"), ("seq", None), ("str", "item1"),
                ("str", "item2")]
    actual = []
    for n in traversal(compose("{key: value, list: [item1, item2]}")):
        short = n.tag.split(":")[-1]
        if short in ("map", "seq"):
            value = None
        else:
            value = n.value
        actual.append((short, value))
    assert expected == actual

def test_as_node():
    for v, tag in ((3, "int"),
                   (3.14159, "float"),
                   ("foo", "str"),
                   (None, "null"),
                   (compose("{}"), "map"),
                   (view(compose("{}")), "map")):
        nd = as_node(v)
        assert nd.tag.split(":")[-1] == tag

def test_str_view():
    v = view(compose("{key: value, list: [item1, item2]}")).str_view
    assert v["key"] == "value"

def test_node_view():
    v = view(compose("{key: value, list: [item1, item2]}")).node_view
    assert v["key"].value == "value"

def test_py_view():
    v = view(compose("{key: 3, list: [item1, item2]}")).py_view
    assert v["key"] == 3

def test_load_filename():
    assert load("/dev/null") == []

def test_load_content():
    v = load("foo", "a: b")
    assert v[0]["a"] == "b"
