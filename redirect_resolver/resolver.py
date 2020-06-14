import logging

import requests

from redirect_resolver.exceptions import (
    CyclicRedirectsError,
    LocationHeaderMissedError,
    MaxBodySizeLimitError,
    MaxRedirectsLimitError,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_BODY_SIZE = 1024 ** 3
DEFAULT_MAX_REDIRECTS = 20
DEFAULT_TIMEOUT_SEC = 10


class Resolver:
    def __init__(
        self,
        method="GET",
        max_body_size=DEFAULT_MAX_BODY_SIZE,
        max_redirects=DEFAULT_MAX_REDIRECTS,
        timeout=DEFAULT_TIMEOUT_SEC,
    ):
        self._method = method
        self._max_body_size = max_body_size
        self._max_redirects = max_redirects
        self._timeout = timeout

    def _handle_response(self, response, url: str) -> str:
        response_next = response.next
        if not response_next:
            logger.error(
                "location header missed: url='%s', status_code=%s",
                url,
                response.status_code,
            )
            raise LocationHeaderMissedError()

        redirect_url = response_next.url

        logger.debug(
            "got redirect to url, base_url='%s', redirect_url='%s' status_code=%s",
            url,
            redirect_url,
            response.status_code,
        )

        content_length_str = response.headers.get("Content-Length")
        if content_length_str:
            try:
                content_length = int(content_length_str)
            except ValueError:
                logger.warning(
                    "invalid Content-Length, ignore error, content_length='%s'",
                    content_length_str,
                )
            else:
                if content_length > self._max_body_size:
                    logger.error(
                        "content length is bigger than max body size, content_length=%d",
                        content_length,
                    )
                    raise MaxBodySizeLimitError(url)

        logger.info("try to read body until max body or until end")

        remain_bytes = self._max_body_size
        for chunk in response.iter_content(self._max_body_size):
            logger.debug("got chunk, chunk_len=%d", len(chunk))
            remain_bytes -= len(chunk)
            if remain_bytes < 0:
                logger.error("max body size limit reached")
                raise MaxBodySizeLimitError(url)

        return redirect_url

    def resolve(self, url: str) -> str:
        seen_urls = {url}
        history = [url]
        with requests.Session() as session:
            for i in range(self._max_redirects):
                logger.debug(
                    "request, url='%s', method='%s', redirect=%d", url, self._method, i
                )
                with session.request(
                    method=self._method,
                    url=url,
                    allow_redirects=False,
                    stream=True,
                    timeout=self._timeout,
                ) as response:
                    if response.status_code < 300 or response.status_code >= 400:
                        logger.info(
                            "got result, url='%s', status_code=%s",
                            url,
                            response.status_code,
                        )
                        return url

                    redirect_url = self._handle_response(response, url)

                if redirect_url in seen_urls:
                    logger.error(
                        "cyclic redirects: cycled_url='%s', history=%s",
                        redirect_url,
                        history,
                    )
                    raise CyclicRedirectsError(history)

                history.append(redirect_url)
                seen_urls.add(redirect_url)

                url = redirect_url

        raise MaxRedirectsLimitError()
