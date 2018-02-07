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

from yaml import ScalarNode, SequenceNode, MappingNode, CollectionNode, Node, compose, compose_all, serialize, \
    serialize_all
from forge.match import choice, match, many
from StringIO import StringIO

from .schema import _scalar2py

# modes
LEAF_AS_NODE = "LEAF_AS_NODE"
LEAF_AS_PYTHON = "LEAF_AS_PYTHON"
LEAF_AS_STRING = "LEAF_AS_STRING"

@match(MappingNode, many(Node))
def traversal(node, *parents):
    yield node
    for k, v in node.value:
        for n in traversal(k):
            yield n
        for n in traversal(v):
            yield n

@match(SequenceNode)
def traversal(node):
    yield node
    for v in node.value:
        for n in traversal(v):
            yield n


@match(ScalarNode)
def traversal(node):
    yield node

@match(MappingNode)
def view(node):
    return MapView(node, LEAF_AS_PYTHON)

@match(SequenceNode)
def view(node):
    return ListView(node, LEAF_AS_PYTHON)

@match(ScalarNode)
def view(node):
    return node

@match(MappingNode, choice(LEAF_AS_NODE, LEAF_AS_STRING, LEAF_AS_PYTHON))
def view(node, mode):
    return MapView(node, mode)

@match(SequenceNode, choice(LEAF_AS_NODE, LEAF_AS_STRING, LEAF_AS_PYTHON))
def view(node, mode):
    return ListView(node, mode)

@match(ScalarNode, LEAF_AS_NODE)
def view(node, _):
    return node

@match(ScalarNode, LEAF_AS_STRING)
def view(node, _):
    return node.value

@match(ScalarNode, LEAF_AS_PYTHON)
def view(node, _):
    return _scalar2py(node)



class View(object):

    @property
    def node_view(self):
        return view(self.node, LEAF_AS_NODE)

    @property
    def str_view(self):
        return view(self.node, LEAF_AS_STRING)

    @property
    def py_view(self):
        return view(self.node, LEAF_AS_PYTHON)


@match(View)
def as_node(v):
    return v.node

@match(Node)
def as_node(n):
    return n

@match(basestring)
def as_node(s):
    return ScalarNode(u'tag:yaml.org,2002:str', s)

@match(choice(int,long))
def as_node(s):
    return ScalarNode(u'tag:yaml.org,2002:int', str(s))

@match(choice(float))
def as_node(s):
    return ScalarNode(u'tag:yaml.org,2002:float', str(s))

@match(None)
def as_node(_):
    return compose("null")


class MapView(View):

    def __init__(self, node, mode):
        self.node = node
        self.mode = mode

    def get(self, key, default=None):
        for k, v in self.node.value:
            if k.value == key:
                return view(v, self.mode)
        return default

    def __getitem__(self, key):
        for k, v in self.node.value:
            if k.value == key:
                return view(v, self.mode)
        raise KeyError(key)

    def __setitem__(self, key, value):
        value = as_node(value)
        values = []
        for k, v in self.node.value:
            if k.value == key:
                values.append((k, value))
                break
            else:
                values.append((k, v))
        else:
            values.append((as_node(key), value))
        self.node.value = values

    def keys(self):
        return set(k.value for k, v in self.node.value)

    def __repr__(self):
        return "{%s}" % ", ".join("%r: %r" % (view(k, LEAF_AS_STRING), view(v, LEAF_AS_STRING))
                                  for k, v in self.node.value)

class ListView(View):

    def __init__(self, node, mode):
        self.node = node
        self.mode = mode

    def __getitem__(self, idx):
        return view(self.node.value[idx], self.mode)

    def __setitem__(self, idx, value):
        self.node.value[idx] = as_node(value)

    def append(self, value):
        self.node.value.append(as_node(value))

    def len(self):
        return len(self.node.value)

    def __repr__(self):
        return repr([v for v in self])

@match(basestring, basestring)
def load(name, content):
    stream = StringIO(content)
    stream.name = name
    return _load(stream)

@match(basestring)
def load(name):
    with open(name) as f:
        return _load(f)

def _load(stream):
    results = []
    for nd in compose_all(stream):
        results.append(view(nd, LEAF_AS_PYTHON))
    return results
