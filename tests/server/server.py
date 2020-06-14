import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Mapping, Optional

from aiohttp import web
from aiohttp.test_utils import TestServer

logger = logging.getLogger(__name__)


@dataclass
class ResponseData:
    status_code: int = 200
    body: bytes = None
    headers: Optional[Mapping[str, str]] = None
    method: str = "get"


class RedirectHandler:
    def __init__(self, response_data: ResponseData):
        self._response_data = response_data

    async def handle_redirect(self, request):
        response_data = self._response_data
        response = web.Response(
            body=response_data.body,
            status=response_data.status_code,
            headers=response_data.headers,
        )
        if "Content-Length" not in response.headers:
            response.enable_chunked_encoding()
        return response


class RedirectTestServer(TestServer):
    def __init__(self, url_to_response_data: Mapping[str, ResponseData]):
        if url_to_response_data is None:
            url_to_response_data = {}
        self._app = web.Application()
        self._app.add_routes(self._build_routes(url_to_response_data))
        super().__init__(app=self._app)

    @staticmethod
    def _build_routes(url_to_response_data):
        routes = []
        for url, response_data in url_to_response_data.items():
            if not response_data:
                response_data = ResponseData()
            redirect_handler = RedirectHandler(response_data).handle_redirect
            routes.append(
                getattr(web, response_data.method.lower())(url, redirect_handler)
            )
        return routes


class ThreadRedirectServer:
    def __init__(self, *args, **kwargs):
        self._test_server = RedirectTestServer(*args, **kwargs)
        self._thread = None
        self._loop = None
        self._start_event = threading.Event()
        self._finish_event = threading.Event()

    def _thread_target(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._test_server.start_server())
        finally:
            self._start_event.set()

        try:
            self._loop.run_forever()
        finally:
            self._finish_event.set()

    @property
    def host(self):
        return self._test_server.host

    @property
    def port(self):
        return self._test_server.port

    @property
    def scheme(self):
        return self._test_server.scheme

    def make_url(self, path):
        return str(self._test_server.make_url(path))

    def run(self):
        logger.info("start server")
        self._thread = threading.Thread(
            target=self._thread_target,
            name="ServerThread-" + str(id(self)),
            daemon=True,
        )
        self._thread.start()
        self._start_event.wait()

    async def _stop_loop(self):
        await self._test_server.close()
        self._loop.stop()

    def stop(self):
        logger.info("stop server")
        asyncio.run_coroutine_threadsafe(self._stop_loop(), self._loop)
        self._finish_event.wait()
