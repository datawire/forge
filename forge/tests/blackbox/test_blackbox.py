import os, pexpect, pytest, sys

DIR = os.path.dirname(__file__)
EXCLUDES = ("__pycache__",)

@pytest.mark.parametrize("directory", [n for n in os.listdir(DIR)
                                       if os.path.isdir(os.path.join(DIR, n)) and n not in EXCLUDES])
def test(directory):
    print

    test_dir = os.path.join(DIR, directory)
    test_spec = os.path.join(test_dir, "test.spec")

    if os.path.exists(test_spec):
        with open(test_spec) as fd:
            ops = fd.read()
    else:
        ops = "RUN forge deploy"

    child = None

    for line in ops.splitlines():
        for stmt in line.split(";"):
            op, arg = stmt.split(None, 1)
            if op == "RUN":
                child = pexpect.spawn(arg, cwd=os.path.join(DIR, directory))
                child.logfile = sys.stdout
            elif op == "OUT":
                child.expect_exact(arg.strip())
            elif op == "TYPE":
                if arg.strip().lower() == "<enter>":
                    child.sendline()
                else:
                    child.sendline(arg)
            else:
                assert False, "unrecognized op: %s" % op

    if child is not None:
        child.expect(pexpect.EOF)
        assert child.wait() == 0
