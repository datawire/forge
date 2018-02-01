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
    return MapView(node)

@match(SequenceNode)
def view(node):
    return ListView(node)

@match(ScalarNode)
def view(node):
    return node


class View(object):
    pass


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

    def __init__(self, node):
        self.node = node

    def get(self, key, default=None):
        for k, v in self.node.value:
            if k.value == key:
                return view(v)
        return default

    def __getitem__(self, key):
        for k, v in self.node.value:
            if k.value == key:
                return view(v)
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

class ListView(View):

    def __init__(self, node):
        self.node = node

    def __getitem__(self, idx):
        return view(self.node.value[idx])

    def __setitem__(self, idx, value):
        self.node.value[idx] = as_node(value)

    def append(self, value):
        self.node.value.append(as_node(value))

    def len(self):
        return len(self.node.value)

