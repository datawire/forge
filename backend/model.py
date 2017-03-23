import sys

from pyrsistent import PClass, PRecord, field, pvector_field

"""
The overall goal of the service registry is to manage a sequence of
updates to a service running in the cloud. Each update is composed of
a service descriptor and an artifact. The basic function of the
registry is to compute the delta between the currently running
descriptor and the update.

"""

if sys.version_info.major == 3:
    from builtins import str
    basestring = str

class Resource(PRecord):
    name = field(type=basestring)
    type = field(type=basestring)

class Descriptor(PRecord):
    artifact = field(type=basestring)
    resources = pvector_field(Resource)

class Task(PRecord):
    type = field(type=basestring)
    resource = field(type=(Resource, basestring))

class Stats(PRecord):
    good = field(type=float)
    bad = field(type=float)
    slow = field(type=float)

class Service(object):

    def __init__(self, name, owner):
        self.name = name
        self.owner = owner
        # the prior descriptors, the head of this is what is currently
        # running
        self.previous = []
        # the target descriptor
        self.update = None
        self.updating = False
        self.stats = Stats(good=0.0, bad=0.0, slow=0.0)

    def json(self):
        return {'name': self.name, 'owner': self.owner, 'stats': self.stats.serialize(),
                'tasks': [t.serialize() for t in self.tasks()]}

    def add(self, descriptor):
        self.update = descriptor

    def tasks(self):
        if self.update:
            if self.previous:
                current_artifact = self.previous[-1].artifact
                current_resources = self.previous[-1].resources
            else:
                current_artifact = None
                current_resources = []
            for resource in self.update.resources:
                if resource not in current_resources:
                    yield Task(type='create', resource=resource)
            for resource in current_resources:
                if resource not in self.update.resources:
                    yield Task(type='orphan', resource=resource)
            if self.update.artifact != current_artifact:
                yield Task(type='deploy', resource=self.update.artifact)

    def go(self):
        self.updating = True

    def done(self):
        if self.updating:
            self.previous.append(self.update)
            self.update = None
            self.updating = False

if __name__ == '__main__':
    s = Service("foo", "bar")
    s.add(Descriptor(artifact="v1", resources=[Resource(name='db', type='postgres')]))
    for t in s.tasks():
        print(t)
    s.go()
    s.done()
    print('--')
    s.add(Descriptor(artifact="v2", resources=[Resource(name='db', type='redis')]))
    for t in s.tasks():
        print(t)
