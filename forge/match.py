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

import inspect, collections, textwrap

class MatchError(Exception):
    pass

EPSILON = object()

class State:

    sequence = 0

    def __init__(self):
        self.id = State.sequence
        State.sequence += 1
        self.matches = {}
        self.epsilons = ()
        self.action = None
        self.match_value = True

    @property
    def transitions(self):
        for s in self.epsilons:
            yield (EPSILON, s)
        for k, v in self.matches.items():
            for s in v:
                yield (k, s)

    @property
    def nodes(self):
        done = set()
        todo = [self]
        while todo:
            state = todo.pop()
            if state not in done:
                yield state
                done.add(state)
            for k, s in state.transitions:
                if s not in done:
                    todo.append(s)

    @property
    def edges(self):
        done = set()
        for state in self.nodes:
            for k, s in state.transitions:
                edge = (state, k, s)
                if edge not in done:
                    yield (state, k, s)
                    done.add(edge)

    @property
    def epsilon_closure(self):
        todo = [self]
        done = set()
        while todo:
            s = todo.pop()
            if s not in done:
                done.add(s)
                for e in s.epsilons:
                    yield e
                    if e not in done:
                        todo.append(e)

    def force(self):
        todo = [self]
        done = set()
        while todo:
            s = todo.pop()
            if s not in done:
                done.add(s)
                for k, v in s.matches.items():
                    if isinstance(k, delay):
                        key = k.force()
                        s.matches[key] = v
                        del s.matches[k]
                    for s2 in v:
                        if s2 not in done:
                            todo.append(s2)
                for e in s.epsilons:
                    if e not in done:
                        todo.append(e)

    def compile(self):
        if self.epsilons:
            assert self.action is None
        actions = set()
        for e in self.epsilon_closure:
            if e.action:
                actions.add(e.action)
            for k, v in e.matches.items():
                for s in v: self.edge(k, s)
        assert len(actions) <= 1, str(self)
        if actions:
            self.action = actions.pop()
        self.epsilons = ()

    def edge(self, *args):
        if len(args) == 1:
            assert isinstance(args[0], State)
            self.epsilons += args
        elif len(args) == 2:
            key, state = args
            self.matches[key] = self.matches.get(key, ()) + (state,)
        else:
            assert False, "wrong number of args"

    def __setitem__(self, key, value):
        self.matches[key] = (value,)

    def __getitem__(self, key):
        return self.matches.get(key, ())

    def __repr__(self):
        transitions = []
        actions = []

        for start, key, end in self.edges:
            if key is EPSILON:
                transitions.append("S%s -> S%s" % (start.id, end.id))
            else:
                transitions.append("S%s %s -> S%s" % (start.id, key, end.id))

        for state in self.nodes:
            if state.action:
                actions.append("S%s(%s)" % (state.id, state.action))

        if transitions:
            return "State(S%s\n  %s\n)" % (self.id, ",\n  ".join(transitions + actions))
        else:
            return "State(S%s)" % self.id

    def match(self, *args, **kwargs):
        states = {self: ()}
        remaining = list(args)
        for value in flatten(args):
            next = {}
            for state, distance in states.items():
                count = 0
                for proj in projections(value, state.match_value):
                    transitions = state[proj]
                    if transitions:
                        for s in transitions:
                            if s not in next:
                                next[s] = distance + (count,)
                    count += 1
            states = next
        nearest = {}
        minimum = None
        for state, distance in states.items():
            if state.action:
                if minimum is None:
                    nearest = {state.action: state}
                    minimum = distance
                elif distance < minimum:
                    nearest = {state.action: state}
                    minimum = distance
                elif distance == minimum:
                    nearest[state.action] = state
        if len(nearest) > 1:
            dfns = "\n".join([ppfun(n.action) for n in nearest.values()])
            raise MatchError("arguments ({}) match multiple actions:\n\n{}".format(ppargs(args), dfns))
        if not nearest:
            dfns = "\n".join([ppfun(n.action) for n in self.nodes if n.action])
            raise MatchError("arguments ({}) do not match:\n\n{}".format(ppargs(args), dfns))
        assert len(nearest) == 1, nearest
        state = nearest.popitem()[1]
        assert state.action, (state, remaining)
        return state.action

    def apply(self, *args, **kwargs):
        return self.match(*args, **kwargs)(*args, **kwargs)


def deduplicate(items):
    deduped = []
    for item in items:
        if not deduped:
            deduped.append([item, 1])
        else:
            last = deduped[-1]
            if last[0] == item:
                last[1] += 1
            else:
                deduped.append([item, 1])

    return [(("%s*%s" % tuple(p)) if p[1] > 1 else "%s" % p[0]) for p in deduped]

def ppargs(args, dedup=False):

    result = []
    for a in args:
        if isinstance(a, list):
            result.append("[%s]" % ppargs(a, True))
        elif isinstance(a, tuple):
            result.append("(%s)" % ppargs(a, True))
        else:
            result.append("%s.%s" % (a.__class__.__module__, a.__class__.__name__))

    if dedup:
        result = deduplicate(result)
    return ", ".join(result)

def ppfun(fun):
    try:
        lines, number = inspect.getsourcelines(fun)
        return "%s:%s:\n%s" % (inspect.getsourcefile(fun), number, "".join(lines))
    except TypeError:
        return repr(fun)

class Marker(object): pass

class Begin(Marker):

    def __init__(self, cls):
        self.cls = cls

    def __hash__(self):
        return hash(self.cls)

    def __eq__(self, other):
        if not isinstance(other, Begin):
            return False
        return self.cls == other.cls

    def __repr__(self):
        return "BEGIN(%s)" % self.cls.__name__

class End(Marker):

    def __repr__(self):
        return "END"

END = End()

def flatten(values):
    for value in values:
        if isinstance(value, (list, tuple)):
            yield Begin(value.__class__)
            for v in flatten(value):
                yield v
            yield END
        else:
            yield value

def projections(value, match_value=True):
    if match_value and isinstance(value, collections.Hashable):
        yield value
    traits = getattr(value, "MATCH_TRAITS", None)
    if traits is not None:
        if isinstance(traits, tuple):
            for t in traits:
                yield t
        else:
            yield traits
    if not isinstance(value, Marker):
        if isinstance(value, super):
            for cls in value.__self_class__.__mro__[1:]:
                yield cls
        else:
            for cls in value.__class__.__mro__:
                yield cls

class Fragment(object):

    def __init__(self, start, extend, doc):
        assert isinstance(start, State)
        self.start = start
        self.extend = extend
        self.doc = doc

def _value(value):
    start = State()
    if isinstance(value, type):
        doc = value.__name__
    elif isinstance(value, lazy):
        doc = value.name
    else:
        doc = repr(value)
    return Fragment(start, lambda next: start.edge(value, next), doc)

def one(*pattern):
    return cat(pattern)

def cat(patterns):
    start = None
    extend = None
    docs = []
    for p in flatten(patterns):
        if isinstance(p, Fragment):
            frag = p
        else:
            frag = _value(p)
        docs.append(frag.doc)
        if start is None:
            start = frag.start
            extend = frag.extend
        else:
            extend(frag.start)
            extend = frag.extend
    if start is None:
        start = State()
        extend = start.edge
    return Fragment(start, extend, ", ".join(docs))

def opt(*pattern):
    frag = cat(pattern)
    return Fragment(frag.start, lambda next: (frag.extend(next), frag.start.edge(next)), "opt(%s)" % frag.doc)

def _many(pattern):
    frag = cat(pattern)
    frag.extend(frag.start)
    return Fragment(frag.start, lambda next: (frag.extend(next), frag.start.edge(next)), "many(%s)" % frag.doc)

def many(*pattern, **kwargs):
    min = kwargs.pop("min", 0)
    if kwargs:
        raise TypeError("no such keyword argument(s): %s" % ", ".join(kwargs.keys()))
    patterns = []
    for i in range(min):
        patterns.extend(pattern)
    patterns.append(_many(pattern))
    return cat(patterns)


def when(pattern, action):
    frag = one(pattern)
    state = State()
    state.action = action
    frag.extend(state)
    if action.__doc__ is not None:
        wrapped = textwrap.fill(action.__doc__, initial_indent="  ", subsequent_indent="  ")
    else:
        wrapped = None
    return Fragment(frag.start, lambda next: state.edge(next), "%s:\n%s" % (frag.doc, wrapped))

def choice(*patterns):
    start = State()
    docs = []
    fragments = [one(p) for p in patterns]
    for f in fragments:
        start.edge(f.start)
        docs.append(f.doc)
    return Fragment(start, lambda next: [f.extend(next) for f in fragments], "choice(%s)" % ", ".join(docs))

def ntuple(pattern, **kwargs):
    return (many(pattern, **kwargs),)

class delay(object):

    def __init__(self, thunk):
        self.thunk = thunk

    def force(self):
        return self.thunk()

class lazy(delay):

    def __init__(self, name):
        self.name = name
        frame = inspect.currentframe()
        try:
            self.frame = frame.f_back
        finally:
            del frame

    def force(self):
        frame = self.frame
        while frame:
            if self.name in frame.f_locals:
                return frame.f_locals[self.name]
            frame = frame.f_back
        raise NameError(self.name)

    def __repr__(self):
        return "lazy(%r)" % self.name

def compile(fragment):
    fragment.start.force()
    todo = [fragment.start]
    done = set()
    while todo:
        state = todo.pop()
        state.compile()
        done.add(state)
        for v in state.matches.values():
            for s in v:
                if s not in done: todo.append(s)
    fragment.start.doc = fragment.doc
    return fragment.start

class _BoundDispatcher(object):

    def __init__(self, clazz, object, dispatcher):
        self.clazz = clazz
        self.object = object
        self.dispatcher = dispatcher

    # XXX: This is here for inspect.ismethoddescriptor which needs to
    # return True for help() to work properly. There may be a better
    # way to do this.
    def __get__(self):
        assert False

    @property
    def __name__(self):
        return self.dispatcher.name

    @property
    def __doc__(self):
        return "\n\n".join([f.__doc__ for c, f in self._mro])

    @property
    def _mro(self):
        for c in self.clazz.__mro__:
            if self.dispatcher.name in c.__dict__:
                disp = c.__dict__[self.dispatcher.name]
                if isinstance(disp, _Dispatcher):
                    yield c, disp

    @property
    def _compiled(self):
        compiled = self.dispatcher.cache.get(self.clazz)
        if compiled is None:
            fragments = []
            for c, disp in self._mro:
                fragments.append(one(c, disp.fragment))
            compiled = compile(choice(*fragments))
            compiled.match_value = False
            self.dispatcher.cache[self.clazz] = compiled
        return compiled

    def __call__(self, *args, **kwargs):
        compiled = self._compiled
        try:
            if self.object is None:
                return compiled.apply(*args, **kwargs)
            else:
                return compiled.apply(self.object, *args, **kwargs)
        except MatchError, e:
            raise TypeError("%s.%s() %s" % (self.clazz.__name__, self.dispatcher.name, e))

    def match(self, *args, **kwargs):
        compiled = self._compiled
        if self.object is None:
            fun = compiled.match(*args, **kwargs)
            return lambda: fun(*args, **kwargs)
        else:
            fun = compiled.match(self.object, *args, **kwargs)
            return lambda: fun(self.object, *args, **kwargs)


class _Dispatcher(object):

    def __init__(self, name):
        self.name = name
        self.fragment = None
        self.compiled = None
        self.cache = {}
        self.docs = []

    def add(self, types, action):
        frag = when(cat(types), action)
        if self.fragment is None:
            self.fragment = frag
        else:
            self.fragment = choice(self.fragment, frag)
        self.compiled = None
        self.docs.append(frag.doc)
        self.__doc__ = "\n\n".join(self.docs)

    def __get__(self, object, clazz):
        return _BoundDispatcher(clazz, object, self)

    @property
    def _compiled(self):
        compiled = self.compiled
        if compiled is None:
            compiled = compile(self.fragment)
            self.compiled = compiled
        return compiled

    def __call__(self, *args, **kwargs):
        compiled = self._compiled
        try:
            return compiled.apply(*args, **kwargs)
        except MatchError, e:
            raise TypeError("%s() %s" % (self.name, e))

    def match(self, *args, **kwargs):
        compiled = self._compiled
        fun = compiled.match(*args, **kwargs)
        return lambda: fun(*args, **kwargs)

def _decorate(namespace, function, pattern):
    name = function.__name__
    if name in namespace and isinstance(namespace[name], _Dispatcher):
        dispatcher = namespace[name]
    else:
        dispatcher = _Dispatcher(name)
        namespace[name] = dispatcher
    dispatcher.add(pattern, function)
    return dispatcher

def match(*pattern):
    def decorator(function):
        namespace = inspect.currentframe().f_back.f_locals
        return _decorate(namespace, function, pattern)
    return decorator

class trait(object):

    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return isinstance(other, trait) and self.value == other.value
