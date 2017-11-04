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

import base64, os, StringIO
from collections import OrderedDict
from yaml import ScalarNode, SequenceNode, MappingNode, CollectionNode, Node, compose_all
from forge.match import match, many, opt

class SchemaError(Exception):
    pass

class Schema(object):

    @match(basestring)
    def load(self, name):
        with open(name) as fd:
            return self.load(name, fd.read())

    @match(basestring, basestring)
    def load(self, name, input):
        stream = StringIO.StringIO(input)
        stream.name = name
        trees = list(compose_all(stream))
        if len(trees) != 1:
            raise SchemaError("%s: expected a single yaml document, found %s documents" % (name, len(trees)))
        tree = trees[0]
        return self.load(tree)

class Scalar(Schema):
    pass

class String(Scalar):

    @match(ScalarNode)
    def load(self, node):
        return node.value

class Base64(Scalar):

    @match(ScalarNode)
    def load(self, node):
        return base64.decodestring(node.value)

class Integer(Scalar):

    @match(ScalarNode)
    def load(self, node):
        return int(node.value)

class Float(Scalar):

    @match(ScalarNode)
    def load(self, node):
        return float(node.value)

class Collection(Schema):
    pass

class Map(Collection):

    @match(Schema)
    def __init__(self, type):
        self.type = type

    @match(MappingNode)
    def load(self, node):
        result = OrderedDict()
        for k, v in node.value:
            result[k.value] = self.type.load(v)
        return result

class Sequence(Collection):

    @match(Schema)
    def __init__(self, type):
        self.type = type

    @match(SequenceNode)
    def load(self, node):
        return [self.type.load(n) for n in node.value]

class Field(object):

    @match(basestring, Schema, opt(basestring), opt(basestring))
    def __init__(self, name, type, alias=None, docs=None):
        self.name = name
        self.type = type
        self.alias = alias

class Class(Schema):

    @match(basestring, object, many(Field))
    def __init__(self, docs, constructor, *fields):
        self.docs = docs
        self.constructor = constructor
        self.fields = OrderedDict()
        for f in fields:
            self.fields[f.name] = f

    @match(object, many(Field))
    def __init__(self, constructor, *fields):
        self.__init__("", constructor, *fields)

    @match(MappingNode)
    def load(self, node):
        loaded = {}
        for k, v in node.value:
            key = k.value
            if key not in self.fields:
                raise SchemaError("no such field: %s\n%s" % (key, k.start_mark))
            f = self.fields[key]
            loaded[f.alias or f.name] = f.type.load(v)
        try:
            return self.constructor(**loaded)
        except SchemaError, e:
            raise SchemaError("%s\n\n%s" % (e, node.start_mark))

class Descriminator(object):

    def __init__(self, field=None):
        self.field = field

    @match(MappingNode)
    def choose(self, node):
        types = [v for k, v in node.value if k.value == self.field]
        if types:
            return types[0].value
        else:
            return "map"

    @match(SequenceNode)
    def choose(self, node):
        return "sequence"

    @match(ScalarNode)
    def choose(self, node):
        return "scalar"

class Union(Schema):

    @match(Descriminator)
    def __init__(self, descriminator, **schemas):
        self.descriminator = descriminator
        self.schemas = schemas

    @match(Node)
    def load(self, node):
        return self.schemas[self.descriminator.choose(node)].load(node)
