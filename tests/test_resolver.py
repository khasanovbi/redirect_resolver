import contextlib

import pytest

from redirect_resolver import exceptions
from redirect_resolver.resolver import Resolver
from server import ResponseData

RESOLVE_START_URL = "/start"


def resolve_url(url_to_response_data, start_url):
    url = start_url
    while True:
        response_data = url_to_response_data[url]
        if not response_data:
            return url

        if not response_data.headers:
            return url

        location = response_data.headers.get("Location")
        if not location:
            return url
        url = location


@pytest.mark.parametrize(
    "url_to_response_data",
    (
        {RESOLVE_START_URL: None},
        {
            RESOLVE_START_URL: ResponseData(
                status_code=302, headers={"Location": "/second"}
            ),
            "/second": None,
        },
    ),
    ids=("no_redirects", "some_redirects"),
)
def test_resolver_success(server_factory, resolver, url_to_response_data):
    server = server_factory(url_to_response_data)
    test_url = server.make_url(RESOLVE_START_URL)

    resolved_url = resolver.resolve(test_url)

    assert resolved_url == server.make_url(
        resolve_url(url_to_response_data, RESOLVE_START_URL)
    )


@pytest.mark.parametrize(
    "url_to_response_data",
    (
        {
            RESOLVE_START_URL: ResponseData(
                status_code=302, headers={"Location": RESOLVE_START_URL}
            )
        },
        {
            RESOLVE_START_URL: ResponseData(
                status_code=302, headers={"Location": "/second"}
            ),
            "/second": ResponseData(status_code=302, headers={"Location": "/third"}),
            "/third": ResponseData(
                status_code=302, headers={"Location": RESOLVE_START_URL}
            ),
        },
    ),
    ids=("same_url_redirect", "multiple_urls_redirects"),
)
def test_resolver_cyclic_redirects(server_factory, resolver, url_to_response_data):
    server = server_factory(url_to_response_data)
    test_url = server.make_url(RESOLVE_START_URL)

    with pytest.raises(exceptions.CyclicRedirectsError):
        resolver.resolve(test_url)


@pytest.mark.parametrize(
    "redirects_server_count, resolver_limit", ((1, 3), (3, 3), (5, 2))
)
def test_max_redirects_limit_error(
    server_factory, redirects_server_count, resolver_limit
):
    url_to_response_data = {
        f"/url-{i}": ResponseData(
            status_code=301, headers={"Location": f"/url-{i + 1}"}
        )
        for i in range(redirects_server_count)
    }
    server = server_factory(url_to_response_data)
    test_url = server.make_url("/url-0")

    resolver = Resolver(max_redirects=resolver_limit)
    if redirects_server_count > resolver_limit:
        context = pytest.raises(exceptions.MaxRedirectsLimitError)
    else:
        context = contextlib.nullcontext()
    with context:
        resolver.resolve(test_url)


def test_location_missed(server_factory, resolver):
    url_to_response_data = {"/missing-location": ResponseData(status_code=301)}
    server = server_factory(url_to_response_data)
    test_url = server.make_url("/missing-location")
    with pytest.raises(exceptions.LocationHeaderMissedError):
        resolver.resolve(test_url)


@pytest.mark.parametrize(
    "server_body_size, resolver_limit",
    ((1024, 2048), (1024, 1024), (1024, 10), (0, 10)),
)
@pytest.mark.parametrize("enable_content_length", (True, False))
def test_max_body_size(
    server_factory, server_body_size, resolver_limit, enable_content_length
):
    body = b"!" * server_body_size
    headers = {"Location": "/ok"}
    if enable_content_length:
        headers["Content-Length"] = f"{len(body)}"

    url_to_response_data = {
        "/max-body-size": ResponseData(status_code=301, body=body, headers=headers),
    }
    server = server_factory(url_to_response_data)
    test_url = server.make_url("/max-body-size")

    resolver = Resolver(max_body_size=resolver_limit)

    if server_body_size > resolver_limit:
        context = pytest.raises(exceptions.MaxBodySizeLimitError)
    else:
        context = contextlib.nullcontext()

    with context:
        resolver.resolve(test_url)
