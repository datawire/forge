# Copyright 2015 datawire. All rights reserved.
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

from forge.match import (
    compile, match, many, opt, when, choice, one, delay, lazy, trait, MatchError
)

class Action(object):

    def __init__(self, label):
        self.label = label
        self.args = None

    def __call__(self, *args):
        self.args = args
        return self

    def __repr__(self):
        return "Action(%s)" % self.label

class Foo(object):
    pass

FOO = Foo()

class Bar(Foo):
    pass

class Baz(object):
    pass

def say(x):
    print x

def test_giant_switch():

    OBJECT = Action("object")
    BAZ = Action("Baz")
    FOO_TYPE = Action("Foo")
    FOO_VALUE = Action("FOO")
    FOO_BAZ = Action("Foo, Baz")
    FOO_OBJECT = Action("Foo, object")
    OBJECT_THREE = Action("object, 3")
    OBJECT_OBJECT = Action("object, object")
    INTS = Action("ints")
    THREES = Action("threes")
    ONE_TO_FOUR = Action("1, 2, 3, 4")
    LIST_OF_INT = Action("list-of-int")
    LIST_OF_ZERO = Action("list-of-zero")
    TUPLE_OF_INT = Action("tuple-of-int")
    PAIRS = Action("PAIRS")

    frag = choice(
        when(object, OBJECT),
        when(Baz, BAZ),
        when(Foo, FOO_TYPE),
        when(FOO, FOO_VALUE),
        when(one(Foo, Baz), FOO_BAZ),
        when(one(Foo, object), FOO_OBJECT),
        when(one(Bar, 3), FOO_OBJECT),
        when(one(object, 3), OBJECT_THREE),
        when(one(object, object), OBJECT_OBJECT),
        when(one(int, many(int)), INTS),
        when(one(3, many(3)), THREES),
        when(one(1, 2, 3, 4), ONE_TO_FOUR),
        when([many(int)], LIST_OF_INT),
        when([0], LIST_OF_ZERO),
        when((int,), TUPLE_OF_INT),
        when(many(str, int), PAIRS)
    )

    n = compile(frag)

    assert n.apply(Foo()) == FOO_TYPE
    assert n.apply(Bar()) == FOO_TYPE
    assert n.apply(Baz()) == BAZ
    assert n.apply(FOO) == FOO_VALUE
    assert n.apply(Foo(), Baz()) == FOO_BAZ
    assert n.apply(Foo(), 3) == FOO_OBJECT
    assert n.apply(Bar(), 3) == FOO_OBJECT
    assert n.apply(object(), object()) == OBJECT_OBJECT
    assert n.apply(3) == THREES
    assert n.apply(3, 3) == THREES
    assert n.apply(3, 3, 3) == THREES
    assert n.apply(3, 3, 3, 3) == THREES
    assert n.apply(1, 2, 3, 4) == ONE_TO_FOUR
    assert n.apply(0, 1, 2, 3) == INTS
    assert n.apply([1, 2, 3, 4]*100) == LIST_OF_INT
    assert n.apply([0]) == LIST_OF_ZERO
    assert n.apply((0,)) == TUPLE_OF_INT
    assert n.apply("one", 1, "two", 2, "three", 3) == PAIRS
    try:
        n.apply("one", 1, "two", 2, "three")
        assert False, "expected MatchError"
    except MatchError:
        pass

@match(int, str)
def asdf(x, y):
    "d1"
    return 1, x, y

@match(str, int)
def asdf(x, y):
    "d2"
    return 2, x, y

@match(3, opt(str))
def asdf(x, y="bleh"):
    "d3"
    return 3, x, y

@match(choice(int, float))
def asdf(x):
    "d4"
    return 4, x

@match(int)
def asdf(x):
    "d5"
    return 5, x

def test_asdf():
    assert asdf(1, "two") == (1, 1, "two")
    assert asdf("one", 2) == (2, "one", 2)
    assert asdf(3) == (3, 3, "bleh")
    assert asdf(3, "fdsa") == (3, 3, "fdsa")
    assert asdf(3.14) == (4, 3.14)

def test_function_doc():
    for i in range(1, 6):
        assert "d%i" % i in asdf.__doc__

class ATest(object):

    @match(str)
    def __init__(self, x):
        "init1"
        self.x = x
        self.case = 1

    @match(int)
    def __init__(self, y):
        "init2"
        self.__init__(str(y))
        self.case = 2

    @match(str, int)
    def foo(self, x, y):
        "foo1"
        return 1, x, y

    @match(int, str)
    def foo(self, x, y):
        "foo2"
        return 2, x, y

    @match([many(int)])
    def foo(self, lst):
        "foo3"
        return 3, lst

class Sub(ATest):

    @match(float)
    def __init__(self, x):
        "init3"
        self.__init__(int(x))
        self.case = 3

    @match(str)
    def foo(self, s):
        "foo4"
        return 4, s

def test_ATest():
    t = ATest(1)
    assert t.case == 2
    assert t.x == "1"

    t = ATest("one")
    assert t.case == 1
    assert t.x == "one"

    assert ATest.foo(t, 1, "two") == (2, 1, "two")
    assert t.foo(1, "two") == (2, 1, "two")
    assert t.foo("one", 2) == (1, "one", 2)
    assert t.foo([1, 2, 3]) == (3, [1, 2, 3])

    s = Sub(3.14)
    assert s.case == 3
    assert s.x == "3"
    assert Sub.foo(s, "asdf") == (4, "asdf")
    assert Sub.foo(s, "asdf", 3) == (1, "asdf", 3)

    s2 = Sub("asdf")
    assert s2.case == 1

    s3 = Sub(3)
    assert s3.case == 2

def test_init_doc():
    for i in range(1, 3):
        assert "init%i" % i in ATest.__init__.__doc__
    assert "init4" not in ATest.__init__.__doc__
    for i in range(1, 4):
        assert "init%i" % i in Sub.__init__.__doc__

def test_method_doc():
    for i in range(1, 4):
        assert "foo%i" % i in ATest.foo.__doc__
    assert "foo5" not in ATest.foo.__doc__
    for i in range(1, 5):
        assert "foo%i" % i in Sub.foo.__doc__

@match(many(int))
def fdsa(*args):
    return args

def test_fdsa():
    assert fdsa() == ()
    assert fdsa(1) == (1,)
    assert fdsa(1, 2) == (1, 2)

@match(int)
def fib(n):
    return fib(n-1) + fib(n-2)

@match(choice(0, 1))
def fib(n):
    return n

def test_fib():
    assert fib(0) == 0
    assert fib(1) == 1
    assert fib(5) == 5
    assert fib(10) == 55
    assert fib(20) == 6765

class Node(object):

    @match(opt(delay(lambda: Node)))
    def __init__(self, parent = None):
        self.parent = parent

def test_delay():
    parent = Node()
    child = Node(parent)
    assert child.parent == parent
    assert parent.parent == None

class LazyNode(object):

    @match(opt(lazy("LazyNode")))
    def __init__(self, parent = None):
        self.parent = parent

def test_lazy():
    parent = LazyNode()
    child = LazyNode(parent)
    assert child.parent == parent
    assert parent.parent == None

class Hasher(object):

    @match(basestring)
    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return hash(self.name)

    @match(delay(lambda: Hasher))
    def __eq__(self, other):
        return self.name == other.name

    @match(object)
    def __eq__(self, other):
        return False

def test_hasher():
    h1 = Hasher("asdf")
    h2 = Hasher("asdf")
    assert h1 == h2
    assert h1 != "asdf"
    assert hash(h1) == hash("asdf")

def a(*args):
    return a
def b(*args):
    return b

def test_choice():
    n = compile(choice(when(choice(str, int), a),
                       when(choice(float, ()), b)))
    assert n.apply(1) == a
    assert n.apply("one") == a
    assert n.apply(1.0) == b
    assert n.apply(()) == b


@match()
def empty_choice():
    return 1

@match(int)
def empty_choice(n):
    return 2

def test_empty_choice():
    assert empty_choice() == 1
    assert empty_choice(3) == 2

@match(choice(basestring))
def nested_choice(n):
    return 1

@match(choice(object, unicode))
def nested_choice(o):
    return 2

def test_nested_choice():
    assert nested_choice("asdf") == 1
    assert nested_choice(u"asdf") == 2

class SuperBase(object):
    pass

class SuperDerived(SuperBase):
    pass

@match(SuperBase)
def superfoo(base):
    return "basic"

@match(SuperDerived)
def superfoo(derived):
    return "derived and " + superfoo(super(SuperDerived, derived))

def test_super():
    assert superfoo(SuperDerived()) == "derived and basic"

class Traitor(object):

    MATCH_TRAITS = trait("T")

@match(trait("T"))
def execute(t):
    return 1

@match(basestring)
def execute(x):
    return 2

def test_traits():
    assert execute(Traitor()) == 1
    assert execute("asdf") == 2

@match(many(int, min=1))
def min1(*n):
    return 1

def test_many_min1():
    try:
        min1()
        assert False
    except TypeError, e:
        assert "do not match" in str(e)
    assert min1(1) == 1
    assert min1(1, 2) == 1

@match(many(int, min=3))
def min3(*n):
    return 1

def test_many_min3():
    for i in range(3):
        try:
            min3(*range(i))
            assert False
        except TypeError, e:
            assert "do not match" in str(e)
    assert min3(1, 2, 3) == 1
    assert min3(1, 2, 3, 4) == 1
    assert min3(1, 2, 3, 4, 5) == 1
