import requests

DEFAULT_MAX_BODY_SIZE = 1024 ** 3
DEFAULT_MAX_REDIRECTS = 20


class Resolver:
    def __init__(
        self,
        method="get",
        max_body_size=DEFAULT_MAX_BODY_SIZE,
        max_redirects=DEFAULT_MAX_REDIRECTS,
    ):
        self._method = method
        self._max_body_size = max_body_size
        self._max_redirects = max_redirects

    def resolve(self, url: str) -> str:
        response = requests.request(
            method=self._method, url=url, allow_redirects=False, stream=True
        )
        return response.headers["Location"]
