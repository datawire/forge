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

    @property
    def docname(self):
        return self.name

    @match(Node)
    def load(self, node):
        raise SchemaError("expecting %s, got %s\n%s" % (self.name, _tag(node), node.start_mark))

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

@match(ScalarNode)
def _scalar2py(node):
    return _scalar2py(node.tag.split(":")[-1], node)

@match("null", ScalarNode)
def _scalar2py(tag, node):
    return None

@match("str", ScalarNode)
def _scalar2py(tag, node):
    return node.value

@match("int", ScalarNode)
def _scalar2py(tag, node):
    return int(node.value)

@match("float", ScalarNode)
def _scalar2py(tag, node):
    return float(node.value)

@match("bool", ScalarNode)
def _scalar2py(tag, node):
    return node.value.lower() == "true"


class Scalar(Schema):

    name = "scalar"
    default_tags = ("string", "integer", "float")

    def __init__(self, *tags):
        self.tags = tags or self.default_tags

    @match(ScalarNode)
    def load(self, node):
        if node.tag.endswith(":null"):
            return None
        else:
            self._check(node)
            return self.decode(node)

    @match(ScalarNode)
    def decode(self, node):
        return _scalar2py(node)

    def _check(self, node):
        actual = _tag(node)
        if actual not in self.tags:
            if len(self.tags) == 1:
                expecting = self.tags[0]
            else:
                expecting = "one of (%s)" % "|".join(self.tags)
            raise SchemaError("expecting %s, got %s" % (expecting, actual))

    @property
    def traversal(self):
        yield self

class Boolean(Scalar):

    name = "boolean"
    default_tags = ("bool",)

    @match(ScalarNode)
    def decode(self, node):
        return node.value.lower() == "true"

    def render(self):
        return "a boolean value"

class String(Scalar):

    name = "string"
    default_tags = ("string",)

    @match(ScalarNode)
    def decode(self, node):
        return node.value

    def render(self):
        return "an unconstrained string"

class Base64(Scalar):

    name = "base64"
    default_tags= ("string",)

    @match(ScalarNode)
    def decode(self, node):
        return base64.decodestring(node.value)

    def render(self):
        return "a base64 encoded string"

class Integer(Scalar):

    name = "integer"
    default_tags = ("integer",)

    @match(ScalarNode)
    def decode(self, node):
        return int(node.value)

    def render(self):
        return "an unconstrained integer"

class Float(Scalar):

    name = "float"
    default_tags = ("float", "integer")

    @match(ScalarNode)
    def decode(self, node):
        return float(node.value)

    def render(self):
        return "an unconstrained float"

class Constant(Scalar):

    def __init__(self, value, type=None):
        Scalar.__init__(self, "string")
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

    @property
    def docname(self):
        return "map[%s]" % self.type.docname

    @match(MappingNode)
    def load(self, node):
        result = OrderedDict()
        for k, v in node.value:
            result[k.value] = self.type.load(v)
        return result

    @property
    def traversal(self):
        yield self
        for t in self.type.traversal:
            yield t

class Sequence(Collection):

    @match(Schema)
    def __init__(self, type):
        self.type = type

    @property
    def name(self):
        return "sequence[%s]" % self.type.name

    @property
    def docname(self):
        return "sequence[%s]" % self.type.docname

    @match(SequenceNode)
    def load(self, node):
        return [self.type.load(n) for n in node.value]

    @property
    def traversal(self):
        yield self
        for t in self.type.traversal:
            yield t

REQUIRED = object()
OMIT = object()

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
        return _scalar2py(node)

    @match(MappingNode)
    def load(self, node):
        result = OrderedDict()
        for k, v in node.value:
            result[k.value] = self.load(v)
        return result

    @match(SequenceNode)
    def load(self, node):
        return [self.load(n) for n in node.value]

    @property
    def traversal(self):
        yield self

class Class(Schema):

    @match(basestring, basestring, object, many(Field))
    def __init__(self, name, docs, constructor, *fields, **kwargs):
        self.name = name
        self.docs = docs
        if isinstance(constructor, Field):
            fields = (constructor,) + fields
            constructor = OrderedDict
        elif not callable(constructor):
            raise TypeError("constructor must be callable")
        self.constructor = constructor
        self.fields = OrderedDict()
        for f in fields:
            self.fields[f.name] = f
        self.strict = kwargs.pop("strict", True)
        if kwargs:
            raise TypeError("no such arg(s): %s" % ", ".join(kwargs.keys()))

    @match(basestring, object, many(Field))
    def __init__(self, name, constructor, *fields):
        self.__init__(name, "", constructor, *fields)

    @match(MappingNode)
    def load(self, node):
        loaded = {}
        for k, v in node.value:
            key = k.value
            if key in self.fields:
                f = self.fields[key]
            elif self.strict:
                raise SchemaError("no such field: %s\n%s" % (key, k.start_mark))
            else:
                f = Field(key, Any())

            loaded[f.alias or f.name] = f.type.load(v)
        for f in self.fields.values():
            key = (f.alias or f.name)
            if key not in loaded:
                if f.default is REQUIRED:
                    raise SchemaError("required field '%s' is missing\n%s" % (f.name, node.start_mark))
                elif f.default is not OMIT:
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

    @property
    def docname(self):
        return '<a href="#%s">%s</a>' % (self.name.replace(":", "_"), self.name)

    def render_all(self):
        types = OrderedDict()
        for t in self.traversal:
            if isinstance(t, Class):
                types[t] = t.render()
        for k, v in types.items():
            print '<div id="%s">' % k.name.replace(":", "_")
            print '<h2>%s</h2>' % k.name
            print
            print v
            print
            print '</div>'

    def render(self):
        result = []
        result.append("<p>")
        result.extend(textwrap.wrap(self.docs.strip()))
        result.append("</p>")
        result.append('<table>')
        result.append("<tr><th>Field</th><th>Type</th><th>Docs</th></tr>")
        for f in self.fields.values():
            docs = "\n".join(textwrap.wrap(f.docs.strip(), initial_indent="    ", subsequent_indent="    ")) \
                                                                               if f.docs else ""
            result.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (f.name, f.type.docname, docs))
        result.append("</table>")
        if result[-1] == "":
            result = result[:-1]
        return "\n".join(result)

@match(String)
def _tag(scalar):
    return "string"

@match(Integer)
def _tag(scalar):
    return "integer"

@match(Float)
def _tag(scalar):
    return "float"

_YAML2ENGLISH={
    "str": "string",
    "int": "integer"
}

@match(ScalarNode)
def _tag(nd):
    tag = nd.tag.split(":")[-1]
    return _YAML2ENGLISH.get(tag, tag)

@match(Sequence)
def _tag(seq):
    return "sequence"

@match(SequenceNode)
def _tag(nd):
    return "sequence"

@match(Map)
def _tag(map):
    return "map"

@match(MappingNode)
def _tag(nd):
    return "map"

class _Signature(object):

    def __init__(self, cls, fields):
        self.cls = cls
        self.fields = fields

    def descriminates(self, other):
        return not self.fields.issubset(other.fields) and not other.fields.issubset(self.fields)

    def __repr__(self):
        stub = "%s:map" % self.cls.name
        if self.fields:
            return "%s{%s}" % (stub, ", ".join("%s=%s" % (n, v) for n, v in sorted(self.fields)))
        else:
            return stub

@match(Class)
def _sig(cls):
    fields = set()
    for f in cls.fields.values():
        if f.required and isinstance(f.type, Constant):
            fields.add((f.name, f.type.value))
    return _Signature(cls, fields)

class Union(Schema):

    """Unions must be able to descriminate between their schemas. The
    means to descriminate can be somewhat flexible. A descriminator is
    computed according to the following algorithm:

    Logically the descriminator consists of the following components:

    1. The type. This is sufficient for scalar values and seqences,
       but we need more to descriminate maps into distinct types.

    2. For maps, a further descriminator is computed based on a
       signature composed of all required fields of type Constant.
    """

    @match(many(Schema, min=1))
    def __init__(self, *schemas):
        self.schemas = schemas

        self.tags = {}
        for s in self.schemas:
            if isinstance(s, Class): continue
            t = _tag(s)
            if t in self.tags:
                raise ValueError("ambiguous union: %s appears multiple times" % t)
            else:
                self.tags[t] = s

        self.signatures = []
        self.constants = {}
        for s in self.schemas:
            if not isinstance(s, Class): continue
            cls_sig = _sig(s)
            for sig in self.signatures:
                if not cls_sig.descriminates(sig):
                    raise ValueError("ambiguous union: %s, %s" % (sig, cls_sig))
            else:
                self.signatures.append(cls_sig)

            for f in s.fields.values():
                if f.required and isinstance(f.type, Constant):
                    if f.name not in self.constants:
                        self.constants[f.name] = {}
                    if f.type.value not in self.constants[f.name]:
                        self.constants[f.name][f.type.value] = set()
                    self.constants[f.name][f.type.value].add(s)

        for s in self.schemas:
            if not isinstance(s, Class): continue
            for f in s.fields.values():
                if not isinstance(f.type, Constant) and f.name in self.constants:
                    raise ValueError("ambiguous union: '%s' both constant and unconstrained" % f.name)

        if self.signatures and "map" in self.tags:
            raise ValueError("ambiguous union: map and %s" % ", ".join(str(s) for s in self.signatures))

    @property
    def name(self):
        return "(%s)" % "|".join(s.name for s in self.schemas)

    @property
    def docname(self):
        return "(%s)" % "|".join(s.docname for s in self.schemas)

    @match(Node)
    def load(self, node):
        t = _tag(node)
        if self.signatures and t == "map":
            candidates = set(s for s in self.schemas if isinstance(s, Class))
            for k, v in node.value:
                if v.tag.endswith(":map") or v.tag.endswith(":seq"): continue
                if k.value in self.constants and v.value in self.constants[k.value]:
                    candidates.intersection_update(self.constants[k.value][v.value])
            if len(candidates) == 1:
                s = candidates.pop()
                return s.load(node)
            else:
                raise SchemaError("expecting one of (%s), got %s" % ("|".join(str(s) for s in self.signatures), t))
        if t not in self.tags:
            raise SchemaError("expecting one of (%s), got %s" % ("|".join(str(s) for s in
                                                                          self.tags.keys() + self.signatures), t))
        return self.tags[t].load(node)

    @property
    def traversal(self):
        for s in self.schemas:
            for t in s.traversal:
                yield t
