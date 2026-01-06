import json
import random
import socket
import ssl
import time
from threading import Thread

from curl_cffi import requests
from websocket import WebSocketApp

from .config import API_TIMEOUT, API_VERSION, DEFAULT_HEADERS, ENDPOINT_SOCKET_IO, LABS_MODELS
from .exceptions import AuthenticationError, InvalidModelError, NetworkError
from .logger import get_logger


class LabsClient:
    """
    A client for interacting with the Perplexity AI Labs API.
    """

    def __init__(self, *, timeout: float = API_TIMEOUT):
        self._logger = get_logger("labs")
        self._timeout = timeout

        self.session = requests.Session(headers=DEFAULT_HEADERS.copy(), impersonate="chrome")
        self.timestamp = format(random.getrandbits(32), "08x")
        self.last_answer = None
        self.history = []

        poll_url = f"{ENDPOINT_SOCKET_IO}?EIO=4&transport=polling&t={self.timestamp}"
        poll_resp = self._request("GET", poll_url)
        self.sid = json.loads(poll_resp.text[1:])["sid"]

        auth_url = (
            f"{ENDPOINT_SOCKET_IO}?EIO=4&transport=polling"
            f"&t={self.timestamp}&sid={self.sid}"
        )
        auth_resp = self._request("POST", auth_url, data='40{"jwt":"anonymous-ask-user"}')
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
        cookies = "; ".join(
            [f"{key}={value}" for key, value in self.session.cookies.get_dict().items()]
        )
        self.ws = WebSocketApp(
            url=websocket_url,
            header={"User-Agent": self.session.headers["User-Agent"]},
            cookie=cookies,
            on_open=lambda ws: (ws.send("2probe"), ws.send("5")),
            on_message=self._on_message,
            on_error=self._on_error,
            socket=self.sock,
        )

        Thread(target=self.ws.run_forever, daemon=True).start()

        while not (self.ws.sock and self.ws.sock.connected):
            time.sleep(0.01)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self) -> None:
        if self.ws:
            self.ws.close()
        if self.sock:
            self.sock.close()
        self.session.close()

    def _request(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", self._timeout)

        try:
            resp = self.session.request(method, url, **kwargs)
        except Exception as exc:  # pragma: no cover - network dependent
            raise NetworkError(f"Request to {url} failed") from exc

        if not resp.ok:
            raise NetworkError(f"HTTP {resp.status_code} error calling {url}")

        return resp

    def _on_message(self, ws, message):
        if message == "2":
            ws.send("3")

        if message.startswith("42"):
            response = json.loads(message[2:])[1]
            if "final" in response:
                self.last_answer = response

    def _on_error(self, ws, error):
        self._logger.warning("Labs websocket error: %s", error)

    def ask(self, query, model: str = "r1-1776", stream: bool = False):
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

        def stream_response():
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

                time.sleep(0.01)

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

            time.sleep(0.01)
