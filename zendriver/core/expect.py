import asyncio
import re
from typing import Union

from .connection import Connection
from .. import cdp


class BaseRequestExpectation:
    def __init__(self, tab: Connection, url_pattern: Union[str, re.Pattern[str]]):
        self.tab = tab
        self.url_pattern = url_pattern
        self.request_future: asyncio.Future[cdp.network.RequestWillBeSent] = (
            asyncio.Future()
        )
        self.response_future: asyncio.Future[cdp.network.ResponseReceived] = (
            asyncio.Future()
        )
        self.request_id: Union[cdp.network.RequestId, None] = None

    async def _request_handler(self, event: cdp.network.RequestWillBeSent):
        if re.fullmatch(self.url_pattern, event.request.url):
            self._remove_request_handler()
            self.request_id = event.request_id
            self.request_future.set_result(event)

    async def _response_handler(self, event: cdp.network.ResponseReceived):
        if event.request_id == self.request_id:
            self._remove_response_handler()
            self.response_future.set_result(event)

    def _remove_request_handler(self):
        self.tab.remove_handlers(cdp.network.RequestWillBeSent, self._request_handler)

    def _remove_response_handler(self):
        self.tab.remove_handlers(cdp.network.ResponseReceived, self._response_handler)

    async def __aenter__(self):
        self.tab.add_handler(cdp.network.RequestWillBeSent, self._request_handler)
        self.tab.add_handler(cdp.network.ResponseReceived, self._response_handler)
        return self

    async def __aexit__(self, *args):
        self._remove_request_handler()
        self._remove_response_handler()

    @property
    async def request(self):
        return (await self.request_future).request

    @property
    async def response(self):
        return (await self.response_future).response

    @property
    async def response_body(self):
        request_id = (await self.request_future).request_id
        body = await self.tab.send(cdp.network.get_response_body(request_id=request_id))
        return body


class RequestExpectation(BaseRequestExpectation):
    @property
    async def value(self) -> cdp.network.RequestWillBeSent:
        return await self.request_future


class ResponseExpectation(BaseRequestExpectation):
    @property
    async def value(self) -> cdp.network.ResponseReceived:
        return await self.response_future


class DownloadExpectation:
    def __init__(self, tab: Connection):
        self.tab = tab
        self.future: asyncio.Future[cdp.page.DownloadWillBegin] = asyncio.Future()
        self.default_behavior = self.tab._download_behavior[0] if self.tab._download_behavior else "default"

    async def _handler(self, event: cdp.page.DownloadWillBegin):

        self._remove_handler()
        self.future.set_result(event)
        # TODO: Stop Download

    def _remove_handler(self):
        self.tab.remove_handlers(cdp.page.DownloadWillBegin, self._handler)

    async def __aenter__(self):
        await self.tab.send(cdp.browser.set_download_behavior(behavior='deny'))
        self.tab.add_handler(cdp.page.DownloadWillBegin, self._handler)
        return self

    async def __aexit__(self, *args):
        await self.tab.send(cdp.browser.set_download_behavior(behavior=self.default_behavior))
        self._remove_handler()

    @property
    async def value(self):
        return await self.future