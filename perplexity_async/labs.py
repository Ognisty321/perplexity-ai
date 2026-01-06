import asyncio
import json
import random
import socket
import ssl
from threading import Thread

from curl_cffi import requests
from websocket import WebSocketApp

from perplexity.config import API_TIMEOUT, API_VERSION, DEFAULT_HEADERS, ENDPOINT_SOCKET_IO, LABS_MODELS
from perplexity.exceptions import AuthenticationError, InvalidModelError, NetworkError
from perplexity.logger import get_logger


class AsyncMixin:
    def __init__(self, *args, **kwargs):
        self.__storedargs = args, kwargs
        self.async_initialized = False

    async def __ainit__(self, *args, **kwargs):
        pass

    async def __initobj(self):
        assert not self.async_initialized
        self.async_initialized = True
        await self.__ainit__(*self.__storedargs[0], **self.__storedargs[1])
        return self

    def __await__(self):
        return self.__initobj().__await__()


class LabsClient(AsyncMixin):
    """
    A client for interacting with the Perplexity AI Labs API.
    """

    async def __ainit__(self, *, timeout: float = API_TIMEOUT):
        self._logger = get_logger("labs")
        self._timeout = timeout
        self.session = requests.AsyncSession(
            headers=DEFAULT_HEADERS.copy(),
            impersonate="chrome",
        )
        self.timestamp = format(random.getrandbits(32), "08x")
        self.last_answer = None
        self.history = []

        poll_url = f"{ENDPOINT_SOCKET_IO}?EIO=4&transport=polling&t={self.timestamp}"
        poll_resp = await self._request("GET", poll_url)
        self.sid = json.loads(poll_resp.text[1:])["sid"]

        auth_url = (
            f"{ENDPOINT_SOCKET_IO}?EIO=4&transport=polling"
            f"&t={self.timestamp}&sid={self.sid}"
        )
        auth_resp = await self._request("POST", auth_url, data='40{"jwt":"anonymous-ask-user"}')
        if auth_resp.text != "OK":
            raise AuthenticationError("Labs authentication failed")

        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        self.sock = context.wrap_socket(
            socket.create_connection(("www.perplexity.ai", 443)),
            server_hostname="www.perplexity.ai",
        )

        websocket_url = (
            "wss://www.perplexity.ai/socket.io/?EIO=4&transport=websocket" f"&sid={self.sid}"
        )
        cookies_string = "; ".join(
            f"{key}={value}" for key, value in self.session.cookies.get_dict().items()
        )
        self.ws = WebSocketApp(
            url=websocket_url,
            header={"User-Agent": self.session.headers["User-Agent"]},
            cookie=cookies_string,
            on_open=lambda ws: (ws.send("2probe"), ws.send("5")),
            on_message=self._on_message,
            on_error=self._on_error,
            socket=self.sock,
        )

        Thread(target=self.ws.run_forever, daemon=True).start()

        while not (self.ws.sock and self.ws.sock.connected):
            await asyncio.sleep(0.01)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self) -> None:
        if self.ws:
            self.ws.close()
        if self.sock:
            self.sock.close()
        closer = getattr(self.session, "aclose", None)
        if callable(closer):
            await closer()
        else:
            self.session.close()

    async def _request(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        try:
            resp = await self.session.request(method, url, **kwargs)
        except Exception as exc:  # pragma: no cover - network dependent
            raise NetworkError(f"Request to {url} failed") from exc

        if not resp.ok:
            raise NetworkError(f"HTTP {resp.status_code} error calling {url}")

        return resp

    def _on_message(self, ws, message):
        try:
            if message == "2":
                ws.send("3")

            if message.startswith("42"):
                response = json.loads(message[2:])[1]
                if "final" in response:
                    self.last_answer = response
        except json.JSONDecodeError as exc:
            self._logger.warning("Labs JSON decode error: %s", exc)
        except Exception as exc:
            self._logger.warning("Labs message handler error: %s", exc)

    def _on_error(self, ws, error):
        self._logger.warning("Labs websocket error: %s", error)

    async def ask(self, query, model: str = "r1-1776", stream: bool = False):
        if model not in LABS_MODELS:
            raise InvalidModelError(f"Invalid labs model '{model}'")

        self.last_answer = None
        self.history.append({"role": "user", "content": query})

        self.ws.send(
            "42"
            + json.dumps(
                [
                    "perplexity_labs",
                    {
                        "messages": self.history,
                        "model": model,
                        "source": "default",
                        "version": API_VERSION,
                    },
                ]
            )
        )

        async def stream_response():
            answer = None

            while True:
                if self.last_answer != answer:
                    answer = self.last_answer
                    yield answer

                if self.last_answer and self.last_answer.get("final"):
                    answer = self.last_answer
                    self.last_answer = None
                    self.history.append(
                        {
                            "role": "assistant",
                            "content": answer["output"],
                            "priority": 0,
                        }
                    )
                    return

                await asyncio.sleep(0.01)

        if stream:
            return stream_response()

        while True:
            if self.last_answer and self.last_answer.get("final"):
                answer = self.last_answer
                self.last_answer = None
                self.history.append(
                    {
                        "role": "assistant",
                        "content": answer["output"],
                        "priority": 0,
                    }
                )
                return answer

            await asyncio.sleep(0.01)
