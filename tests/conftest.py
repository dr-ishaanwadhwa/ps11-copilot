import pytest

from copilot.load import load_pack


@pytest.fixture(scope="session")
def pack():
    return load_pack()


@pytest.fixture(scope="session")
def matches(pack):
    from copilot.match import match_all
    return match_all(pack)


@pytest.fixture(scope="session")
def copilot(pack):
    from copilot.answers import Copilot
    return Copilot(pack)
