import pytest

from redirect_resolver.resolver import Resolver


@pytest.fixture
def resolver():
    return Resolver()


def test_resolver_success(resolver):
    assert resolver.resolve("http://ya.ru") == "https://ya.ru"
