
from .common import defuzz, tokenize

def test_defuzz():
    s = defuzz("stuff 2c7e6f384c1371406c43d7a6e8c913f5903236ad.sha, more test_id_123_4 stuff, 2c7e6f384c1371406c43d7a6e8c913f5903236ad.git, 2c7e6f384c1371406c43d7a6e8c913f5903236ad.git, and even more stuff")
    assert s == "stuff VERSION_1, more TEST_ID_1 stuff, VERSION_2, VERSION_2, and even more stuff"
