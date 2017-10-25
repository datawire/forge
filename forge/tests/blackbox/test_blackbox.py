import os, pytest

from forge.tasks import sh

DIR = os.path.dirname(__file__)
EXCLUDES = ("__pycache__",)

@pytest.mark.parametrize("directory", [n for n in os.listdir(DIR)
                                       if os.path.isdir(os.path.join(DIR, n)) and n not in EXCLUDES])
def test(directory):
    output = sh("forge", "deploy", cwd=os.path.join(DIR, directory))
    assert output.code == 0
