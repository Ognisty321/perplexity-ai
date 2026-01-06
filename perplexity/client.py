import mimetypes
import re
from typing import Dict, Generator, Iterable, List, Mapping, Optional, Tuple, Union
from uuid import uuid4

from curl_cffi import CurlMime, requests

from .config import (
    ACCOUNT_TIMEOUT,
    API_TIMEOUT,
    API_VERSION,
    DEFAULT_COPILOT_QUERIES,
    DEFAULT_FILE_UPLOADS,
    DEFAULT_HEADERS,
    DEFAULT_PROMPT_SOURCE,
    DEFAULT_QUERY_SOURCE,
    DEFAULT_SEARCH_FOCUS,
    DEFAULT_SEND_BACK_TEXT_IN_STREAMING_API,
    DEFAULT_SUPPORTED_BLOCK_USE_CASES,
    DEFAULT_SUPPORTED_FEATURES,
    DEFAULT_TIMEZONE,
    DEFAULT_USE_SCHEMATIZED_API,
    DEFAULT_ALWAYS_SEARCH_OVERRIDE,
    DEFAULT_BROWSER_AGENT_ALLOW_ONCE_FROM_TOGGLE,
    DEFAULT_FORCE_ENABLE_BROWSER_AGENT,
    DEFAULT_IS_RELATED_QUERY,
    DEFAULT_IS_SPONSORED,
    DEFAULT_LOCAL_SEARCH_ENABLED,
    DEFAULT_NAV_SUGGESTIONS_DISABLED,
    DEFAULT_OVERRIDE_NO_SEARCH,
    DEFAULT_SHOULD_ASK_FOR_MCP_TOOL_CONFIRMATION,
    DEFAULT_SKIP_SEARCH_ENABLED,
    EMAIL_SUBJECT_PATTERN,
    ENDPOINT_ATTACHMENT_PROCESSING_SUBSCRIBE,
    ENDPOINT_AUTH_SESSION,
    ENDPOINT_AUTH_SIGNIN,
    ENDPOINT_SSE_ASK,
    ENDPOINT_UPLOAD_URL,
    MODEL_MAPPINGS,
    SEARCH_LANGUAGES,
    SIGNIN_URL_PATTERN,
)
from .emailnator import Emailnator
from .exceptions import (
    AccountCreationError,
    AuthenticationError,
    FileUploadError,
    NetworkError,
    RateLimitError,
    ValidationError,
)
from .logger import get_logger
from .utils import (
    normalize_files,
    parse_sse_chunk,
    sanitize_query,
    validate_query_limits,
    validate_search_params,
)

FileData = Union[str, bytes, bytearray, memoryview]
PRO_MODES = {"pro", "reasoning", "deep research"}
IMAGE_UPLOAD_PATH_RE = re.compile(r"/private/s--.*?--/v\d+/user_uploads/")


class Client:
    """
    A client for interacting with the Perplexity AI API.
    """

    def __init__(
        self,
        cookies: Optional[dict] = None,
        *,
        headers: Optional[dict] = None,
        timeout: float = API_TIMEOUT,
    ):
        session_headers = DEFAULT_HEADERS.copy()
        if headers:
            session_headers.update(headers)

        cookies = cookies or {}
        self.session = requests.Session(
            headers=session_headers,
            cookies=cookies,
            impersonate="chrome",
        )
        self._timeout = timeout
        self._logger = get_logger("client")

        self.own = bool(cookies)
        self.copilot = float("inf") if self.own else 0
        self.file_upload = float("inf") if self.own else 0
        self.signin_regex = re.compile(SIGNIN_URL_PATTERN)

        self._init_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self) -> None:
        self.session.close()

    def _init_session(self) -> None:
        try:
            resp = self.session.get(ENDPOINT_AUTH_SESSION, timeout=self._timeout)
        except Exception as exc:  # pragma: no cover - network dependent
            raise NetworkError("Failed to initialize session") from exc

        if not resp.ok:
            self._raise_for_status(resp, ENDPOINT_AUTH_SESSION)

    def _raise_for_status(self, resp, url: str) -> None:
        status = getattr(resp, "status_code", None)
        message = f"HTTP {status} error calling {url}"

        if status in (401, 403):
            raise AuthenticationError(message)
        if status == 429:
            raise RateLimitError(message)

        raise NetworkError(message)

    def _request(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", self._timeout)

        try:
            resp = self.session.request(method, url, **kwargs)
        except Exception as exc:  # pragma: no cover - network dependent
            raise NetworkError(f"Request to {url} failed") from exc

        if not resp.ok:
            self._raise_for_status(resp, url)

        return resp

    def create_account(
        self,
        cookies: dict,
        *,
        max_attempts: int = 3,
        timeout: int = ACCOUNT_TIMEOUT,
    ) -> bool:
        """
        Creates a new account using Emailnator cookies.
        """
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                emailnator_cli = Emailnator(cookies)
                csrf_cookie = self.session.cookies.get_dict().get("next-auth.csrf-token")
                if not csrf_cookie:
                    raise AuthenticationError("Missing CSRF token in session cookies")

                csrf_token = csrf_cookie.split("%")[0]
                self._request(
                    "POST",
                    ENDPOINT_AUTH_SIGNIN,
                    data={
                        "email": emailnator_cli.email,
                        "csrfToken": csrf_token,
                        "callbackUrl": "https://www.perplexity.ai/",
                        "json": "true",
                    },
                )
                new_msgs = emailnator_cli.reload(
                    wait_for=lambda x: x.get("subject") == EMAIL_SUBJECT_PATTERN,
                    timeout=timeout,
                )
                if not new_msgs:
                    self._logger.warning("Account creation attempt %s timed out", attempt)
                    continue

                msg = emailnator_cli.get(
                    func=lambda x: x.get("subject") == EMAIL_SUBJECT_PATTERN
                )
                if not msg:
                    self._logger.warning("Account creation attempt %s had no email", attempt)
                    continue

                msg_body = emailnator_cli.open(msg["messageID"])
                match = self.signin_regex.search(msg_body)
                if not match:
                    raise AccountCreationError("Sign-in link not found in email message")

                self._request("GET", match.group(1))
                self.own = True
                self.copilot = DEFAULT_COPILOT_QUERIES
                self.file_upload = DEFAULT_FILE_UPLOADS
                return True
            except Exception as exc:
                last_error = exc
                self._logger.warning("Account creation attempt %s failed: %s", attempt, exc)

        raise AccountCreationError("Failed to create account") from last_error

    def _normalize_follow_up(self, follow_up: Optional[dict]) -> Tuple[List[str], Optional[str]]:
        if not follow_up:
            return [], None
        if not isinstance(follow_up, dict):
            raise ValidationError("follow_up must be a dict")

        attachments = follow_up.get("attachments") or []
        if not isinstance(attachments, list):
            raise ValidationError("follow_up.attachments must be a list")

        backend_uuid = follow_up.get("backend_uuid")
        return attachments, backend_uuid

    def _upload_files(self, files: Mapping[str, bytes]) -> Tuple[List[str], List[str]]:
        uploaded_files: List[str] = []
        uploaded_file_uuids: List[str] = []
        file_payloads: Dict[str, Dict[str, object]] = {}
        file_parts: Dict[str, Tuple[str, bytes, str]] = {}
        file_order: List[str] = []

        for filename, data in files.items():
            file_uuid = str(uuid4())
            guessed_type = mimetypes.guess_type(filename)[0]
            payload_content_type = guessed_type or ""
            file_type = guessed_type or "application/octet-stream"
            file_payloads[file_uuid] = {
                "filename": filename,
                "content_type": payload_content_type,
                "source": "default",
                "file_size": len(data),
                "force_image": False,
            }
            file_parts[file_uuid] = (filename, data, file_type)
            file_order.append(file_uuid)

        try:
            upload_info_resp = self._request(
                "POST",
                ENDPOINT_UPLOAD_URL,
                params={"version": API_VERSION, "source": "default"},
                json={"files": file_payloads},
            )
            upload_info = upload_info_resp.json()
        except Exception as exc:
            raise FileUploadError("Failed to create upload URLs") from exc

        if not isinstance(upload_info, dict):
            raise FileUploadError("Invalid upload metadata response")

        results = upload_info.get("results")
        if results is None and len(file_order) == 1 and "s3_bucket_url" in upload_info:
            results = {file_order[0]: upload_info}

        if not isinstance(results, dict):
            raise FileUploadError("Upload metadata missing results")

        for file_uuid in file_order:
            file_upload_info = results.get(file_uuid)
            if not isinstance(file_upload_info, dict):
                raise FileUploadError(f"Upload metadata missing for file {file_uuid}")
            if file_upload_info.get("rate_limited"):
                raise RateLimitError("File upload rate limited")
            if file_upload_info.get("error"):
                raise FileUploadError(
                    f"Upload metadata error for {file_uuid}: {file_upload_info.get('error')}"
                )

            fields = file_upload_info.get("fields")
            bucket_url = file_upload_info.get("s3_bucket_url")
            if not fields or not bucket_url:
                raise FileUploadError("Upload metadata missing required fields")

            filename, data, file_type = file_parts[file_uuid]

            mp = CurlMime()
            for key, value in fields.items():
                mp.addpart(name=key, data=value)
            mp.addpart(
                name="file",
                content_type=file_type,
                filename=filename,
                data=data,
            )

            upload_resp = self._request("POST", bucket_url, multipart=mp)
            uploaded_files.append(self._resolve_uploaded_url(file_upload_info, upload_resp))
            uploaded_file_uuids.append(str(file_upload_info.get("file_uuid") or file_uuid))

        return uploaded_files, uploaded_file_uuids

    def _subscribe_attachment_processing(
        self,
        file_uuids: List[str],
        *,
        timeout: Optional[float] = None,
    ) -> Optional[dict]:
        if not file_uuids:
            return None

        resp = self._request(
            "POST",
            ENDPOINT_ATTACHMENT_PROCESSING_SUBSCRIBE,
            json={"file_uuids": file_uuids},
            stream=True,
            timeout=timeout or self._timeout,
        )
        return self._collect_response(resp)

    def _resolve_uploaded_url(self, file_upload_info: dict, upload_resp) -> str:
        s3_object_url = file_upload_info.get("s3_object_url")
        if not s3_object_url:
            raise FileUploadError("Upload response missing s3_object_url")

        if "image/upload" in s3_object_url:
            try:
                secure_url = upload_resp.json().get("secure_url")
            except Exception as exc:
                raise FileUploadError("Image upload did not return JSON") from exc

            if not secure_url:
                raise FileUploadError("Image upload response missing secure_url")

            return IMAGE_UPLOAD_PATH_RE.sub("/private/user_uploads/", secure_url)

        return s3_object_url

    def _iter_sse_messages(self, resp) -> Iterable[dict]:
        for chunk in resp.iter_lines(delimiter=b"\r\n\r\n"):
            if not chunk:
                continue
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="ignore")

            event, payload = parse_sse_chunk(chunk)
            if event == "message" and payload is not None:
                yield payload
            elif event == "end_of_stream":
                break

    def _stream_response(self, resp) -> Generator[dict, None, None]:
        try:
            for payload in self._iter_sse_messages(resp):
                yield payload
        finally:
            resp.close()

    def _collect_response(self, resp) -> dict:
        try:
            last_payload: dict = {}
            for payload in self._iter_sse_messages(resp):
                last_payload = payload
            return last_payload
        finally:
            resp.close()

    def search(
        self,
        query: str,
        mode: str = "auto",
        model: Optional[str] = None,
        sources: Optional[List[str]] = None,
        files: Optional[Dict[str, FileData]] = None,
        stream: bool = False,
        language: str = "en-US",
        follow_up: Optional[dict] = None,
        incognito: bool = False,
        timezone: Optional[str] = None,
        search_focus: Optional[str] = None,
        search_recency_filter: Optional[str] = None,
        prompt_source: Optional[str] = None,
        query_source: Optional[str] = None,
        supported_block_use_cases: Optional[List[str]] = None,
        supported_features: Optional[List[str]] = None,
        time_from_first_type: Optional[float] = None,
        dsl_query: Optional[str] = None,
        params_overrides: Optional[Dict[str, object]] = None,
        wait_for_attachment_processing: bool = False,
        attachment_processing_timeout: Optional[float] = None,
    ):
        """
        Executes a search query on Perplexity AI.
        """
        query = sanitize_query(query)
        if sources is None:
            sources = ["web"]
        if files is None:
            files = {}

        validate_search_params(mode, model, sources, self.own)
        normalized_files = normalize_files(files) if files else {}
        validate_query_limits(self.copilot, self.file_upload, mode, len(normalized_files))

        if language not in SEARCH_LANGUAGES:
            self._logger.warning("Language '%s' is not in the supported list", language)

        attachments, backend_uuid = self._normalize_follow_up(follow_up)
        if normalized_files:
            uploaded_files, uploaded_file_uuids = self._upload_files(normalized_files)
            if wait_for_attachment_processing:
                self._subscribe_attachment_processing(
                    uploaded_file_uuids,
                    timeout=attachment_processing_timeout,
                )
        else:
            uploaded_files, uploaded_file_uuids = [], []

        try:
            model_preference = MODEL_MAPPINGS[mode][model]
        except KeyError as exc:
            raise ValidationError("Invalid model mapping configuration") from exc

        params = {
            "attachments": uploaded_files + attachments,
            "language": language,
            "timezone": timezone or DEFAULT_TIMEZONE,
            "search_focus": search_focus or DEFAULT_SEARCH_FOCUS,
            "sources": sources,
            "search_recency_filter": search_recency_filter,
            "frontend_uuid": str(uuid4()),
            "mode": "concise" if mode == "auto" else "copilot",
            "model_preference": model_preference,
            "is_related_query": DEFAULT_IS_RELATED_QUERY,
            "is_sponsored": DEFAULT_IS_SPONSORED,
            "frontend_context_uuid": str(uuid4()),
            "prompt_source": prompt_source or DEFAULT_PROMPT_SOURCE,
            "query_source": query_source or DEFAULT_QUERY_SOURCE,
            "is_incognito": incognito,
            "time_from_first_type": time_from_first_type,
            "local_search_enabled": DEFAULT_LOCAL_SEARCH_ENABLED,
            "use_schematized_api": DEFAULT_USE_SCHEMATIZED_API,
            "send_back_text_in_streaming_api": DEFAULT_SEND_BACK_TEXT_IN_STREAMING_API,
            "supported_block_use_cases": supported_block_use_cases
            or DEFAULT_SUPPORTED_BLOCK_USE_CASES,
            "client_coordinates": None,
            "mentions": [],
            "dsl_query": dsl_query or query,
            "skip_search_enabled": DEFAULT_SKIP_SEARCH_ENABLED,
            "is_nav_suggestions_disabled": DEFAULT_NAV_SUGGESTIONS_DISABLED,
            "source": "default",
            "always_search_override": DEFAULT_ALWAYS_SEARCH_OVERRIDE,
            "override_no_search": DEFAULT_OVERRIDE_NO_SEARCH,
            "should_ask_for_mcp_tool_confirmation": DEFAULT_SHOULD_ASK_FOR_MCP_TOOL_CONFIRMATION,
            "browser_agent_allow_once_from_toggle": DEFAULT_BROWSER_AGENT_ALLOW_ONCE_FROM_TOGGLE,
            "force_enable_browser_agent": DEFAULT_FORCE_ENABLE_BROWSER_AGENT,
            "supported_features": supported_features or DEFAULT_SUPPORTED_FEATURES,
            "version": API_VERSION,
        }
        if backend_uuid:
            params["last_backend_uuid"] = backend_uuid
        if params_overrides:
            params.update(params_overrides)

        json_data = {"query_str": query, "params": params}

        resp = self._request("POST", ENDPOINT_SSE_ASK, json=json_data, stream=True)

        if mode in PRO_MODES:
            self.copilot -= 1
        if normalized_files:
            self.file_upload -= len(normalized_files)

        if stream:
            return self._stream_response(resp)

        return self._collect_response(resp)
