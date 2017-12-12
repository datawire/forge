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

import base64, os, StringIO, textwrap
from collections import OrderedDict
from yaml import ScalarNode, SequenceNode, MappingNode, CollectionNode, Node, compose_all
from forge.match import match, many, opt

class SchemaError(Exception):
    pass

class Schema(object):

    @match(Node)
    def load(self, node):
        raise SchemaError("expecting %s, got %s\n%s" % (self.name, node.tag, node.start_mark))

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

    @match(ScalarNode)
    def load(self, node):
        if node.tag.endswith(":null"):
            return None
        else:
            return self.decode(node)

class String(Scalar):

    name = "string"

    @match(ScalarNode)
    def decode(self, node):
        return node.value

    @property
    def traversal(self):
        yield self

    def render(self):
        return "an unconstrained string"

class Base64(Scalar):

    name = "base64"

    @match(ScalarNode)
    def decode(self, node):
        return base64.decodestring(node.value)

    @property
    def traversal(self):
        yield self

    def render(self):
        return "a base64 encoded string"

class Integer(Scalar):

    name = "integer"

    @match(ScalarNode)
    def decode(self, node):
        return int(node.value)

    @property
    def traversal(self):
        yield self

    def render(self):
        return "an unconstrained integer"

class Float(Scalar):

    name = "float"

    @match(ScalarNode)
    def decode(self, node):
        return float(node.value)

    @property
    def traversal(self):
        yield self

    def render(self):
        return "an unconstrained float"

class Constant(Scalar):

    def __init__(self, value, type=None):
        self.value = value
        self.type = type or String()

    @property
    def name(self):
        return repr(self.value)

    @match(ScalarNode)
    def decode(self, node):
        value = self.type.load(node)
        if self.value != value:
            raise SchemaError("expected %s, got %s\n%s" % (self.value, value, node.start_mark))
        return value

    @property
    def traversal(self):
        yield self
        for t in self.type.traversal:
            yield t

    def render(self):
        return "A %s constant of %s." % (self.type.name, self.name)

class Collection(Schema):
    pass

class Map(Collection):

    @match(Schema)
    def __init__(self, type):
        self.type = type

    @property
    def name(self):
        return "map[%s]" % self.type.name

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

    @property
    def name(self):
        return "sequence[%s]" % self.type.name

    @match(SequenceNode)
    def load(self, node):
        return [self.type.load(n) for n in node.value]

REQUIRED = object()

class Field(object):

    @match(basestring, Schema, opt(basestring), opt(basestring), opt(object))
    def __init__(self, name, type, alias=None, docs=None, default=REQUIRED):
        self.name = name
        self.type = type
        self.alias = alias
        self.docs = docs
        self.default = default

    @property
    def required(self):
        return self.default is REQUIRED

class Any(Schema):

    name = "any"

    @match(ScalarNode)
    def load(self, node):
        return self.decode(node.tag.split(":")[-1], node)

    @match("null", ScalarNode)
    def decode(self, tag, node):
        return None

    @match("str", ScalarNode)
    def decode(self, tag, node):
        return node.value

    @match("int", ScalarNode)
    def decode(self, tag, node):
        return int(node.value)

    @match("float", ScalarNode)
    def decode(self, tag, node):
        return float(node.value)

    @match(MappingNode)
    def load(self, node):
        result = OrderedDict()
        for k, v in node.value:
            result[k.value] = self.load(v)
        return result

    @match(SequenceNode)
    def load(self, node):
        return [self.load(n) for n in node.value]

class Class(Schema):

    @match(basestring, basestring, object, many(Field))
    def __init__(self, name, docs, constructor, *fields):
        self.name = name
        self.docs = docs
        if isinstance(constructor, Field):
            raise TypeError("missing constructor")
        if not callable(constructor):
            raise TypeError("constructor must be callable")
        self.constructor = constructor
        self.fields = OrderedDict()
        for f in fields:
            self.fields[f.name] = f

    @match(basestring, object, many(Field))
    def __init__(self, name, constructor, *fields):
        self.__init__(name, "", constructor, *fields)

    @match(MappingNode)
    def load(self, node):
        loaded = {}
        for k, v in node.value:
            key = k.value
            if key not in self.fields:
                raise SchemaError("no such field: %s\n%s" % (key, k.start_mark))
            f = self.fields[key]
            loaded[f.alias or f.name] = f.type.load(v)
        for f in self.fields.values():
            key = (f.alias or f.name)
            if key not in loaded:
                if f.default is REQUIRED:
                    raise SchemaError("required field '%s' is missing\n%s" % (f.name, node.start_mark))
                else:
                    loaded[key] = f.default
        try:
            return self.constructor(**loaded)
        except SchemaError, e:
            raise SchemaError("%s\n\n%s" % (e, node.start_mark))

    @property
    def traversal(self):
        yield self
        for f in self.fields.values():
            for t in f.type.traversal:
                yield t

    def render_all(self):
        types = OrderedDict()
        for t in self.traversal:
            if isinstance(t, Class):
                types[t.name] = t.render()
        for k, v in types.items():
            print "## %s" % k
            print
            print v
            print

    def render(self):
        result = []
        result.extend(textwrap.wrap(self.docs.strip()))
        result.append("")
        for f in self.fields.values():
            result.append(" - %s: %s" % (f.name, f.type.name))
            if f.docs:
                result.append("")
                result.extend(textwrap.wrap(f.docs.strip(), initial_indent="    ", subsequent_indent="    "))
            result.append("")
        if result[-1] == "":
            result = result[:-1]
        return "\n".join(result)

class Union(Schema):

    @match(many(Schema, min=1))
    def __init__(self, *schemas):
        self.schemas = schemas

    @property
    def name(self):
        return "(%s)" % "|".join(s.name for s in self.schemas)

    @match(Node)
    def load(self, node):
        for s in self.schemas:
            try:
                return s.load(node)
            except SchemaError, e:
                pass
        raise SchemaError("expecting one of (%s), got %s\n%s" % ("|".join((s.name for s in self.schemas)),
                                                                 node.tag, node.start_mark))

    @property
    def traversal(self):
        for s in self.schemas:
            for t in s.traversal:
                yield t
