import glob, os, pexpect, pytest, sys, time
from forge.tests.common import mktree, defuzz, match

DIR = os.path.dirname(__file__)

SPECS = [os.path.relpath(n, DIR) for n in glob.glob(os.path.join(DIR, "*/*.spec"))] + \
        [os.path.relpath(n, DIR) for n in glob.glob(os.path.join(DIR, "*.spec"))]

TEST_ID = ("test_id_%s" % time.time()).replace(".", "_")

@pytest.mark.parametrize("spec", SPECS)
def test(spec):
    print

    test_spec = os.path.join(DIR, spec)
    test_dir = os.path.dirname(test_spec)

    if not os.path.samefile(DIR, test_dir):
        tree = {
            "forge.yaml": """
# Global forge configuration
# Normally you would not want to check this into git, but this is here
# for testing purposes.

docker-repo: registry.hub.docker.com/forgeorg
user: forgetest
password: >
  Zm9yZ2V0ZXN0
        """
        }

        for path, dirs, files in os.walk(test_dir):
            for name in files:
                key = os.path.join(os.path.relpath(path, test_dir), name)
                if key.startswith("./"):
                    key = key[2:]
                with open(os.path.join(path, name), "r") as fd:
                    tree[key] = fd.read()
    else:
        tree = {}

    root = mktree(tree, TEST_ID=TEST_ID)
    print "TEST_ID: %s" % TEST_ID
    print "TEST_BASE: %s" % root

    with open(test_spec) as fd:
        ops = fd.read()

    runner = Runner(root, ops)
    runner.run()

MULTILINE = "MULTILINE"
DEFAULT = "DEFAULT"

class Runner(object):

    multiline = ('MATCH', 'FILE')

    def __init__(self, base, spec):
        self.base = base
        self.cwd = base
        self.spec = spec
        self.child = None

    def run(self):
        mode = DEFAULT

        for line in self.spec.splitlines():
            if mode == DEFAULT:
                if not line.strip(): continue
                for stmt in line.split(";"):
                    if mode == MULTILINE:
                        raise Exception("multiline op must be last in line")
                    parts = stmt.split(None, 1)
                    op = parts.pop(0)
                    arg = parts.pop(0) if parts else None
                    if op in self.multiline:
                        mode = MULTILINE
                        body = ""
                        continue
                    else:
                        self.dispatch(op, arg)
            elif mode == MULTILINE:
                if line.rstrip() == "END":
                    mode = DEFAULT
                    self.dispatch(op, arg, body)
                else:
                    body += line + "\n"

        if mode == MULTILINE:
            raise Exception("unterminated multiline op")

        self.wait()

    def dispatch(self, op, arg, body=None):
        attr = getattr(self, "do_%s" % op, None)
        if attr is None:
            assert False, "unrecognized op: %s" % op
        elif op in self.multiline:
            attr(arg, body)
        else:
            attr(arg)

    def wait(self):
        if self.child is not None:
            self.child.expect(pexpect.EOF)
            assert self.child.wait() == 0

    def do_RUN(self, arg):
        self.wait()
        print "RUN", arg
        self.child = pexpect.spawn(arg, cwd=self.cwd)
        self.child.logfile = sys.stdout

    def do_CWD(self, arg):
        self.cwd = os.path.join(self.base, arg)

    def do_OUT(self, arg):
        self.child.expect_exact(arg.strip())

    def do_NOT(self, arg):
        self.child.expect(pexpect.EOF)
        assert arg not in self.child.before

    def do_TYPE(self, arg):
        if arg.strip().lower() == "<enter>":
            self.child.sendline()
        elif arg.strip().lower() == "<esc>":
            self.child.send("\x1B")
        else:
            self.child.sendline(arg)

    def do_EOF(self, arg):
        self.child.sendeof()

    def do_ERR(self, arg):
        self.child.expect(pexpect.EOF)
        assert self.child.wait() != 0
        self.child = None

    def do_MATCH(self, _, pattern):
        pattern = unicode(pattern).strip()
        self.child.expect(pexpect.EOF)
        output = self.child.before.strip()
        defuzzed = defuzz(output.replace(TEST_ID, "TEST_ID").replace(self.base, "TEST_BASE"))
        if not match(defuzzed, pattern.strip()):
            print "OUTPUT:"
            print output
            print "DEFUZZED OUTPUT:"
            print defuzzed
            print "PATTERN:"
            print pattern
            assert False

    def do_FILE(self, name, body):
        self.wait()
        path = os.path.join(self.cwd, name)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, "write") as fd:
            fd.write(body.replace("TEST_ID", TEST_ID))
