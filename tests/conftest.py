import pytest

from redirect_resolver.resolver import Resolver
from server import ThreadRedirectServer


@pytest.fixture
def resolver():
    return Resolver()


@pytest.fixture
def server_factory(request):
    def get_server(url_to_response_data):
        server = ThreadRedirectServer(url_to_response_data=url_to_response_data)
        server.run()
        request.addfinalizer(server.stop)
        return server

    return get_server
