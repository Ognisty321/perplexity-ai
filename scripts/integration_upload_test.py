#!/usr/bin/env python3
"""
Integration test for Perplexity upload + SSE flow.

Reads cookies from environment variables (optionally loaded from .env):
  - PPLX_CSRF_TOKEN
  - PPLX_SESSION_TOKEN

Optional environment variables:
  - PPLX_QUERY (default: "Summarize the attached file.")
  - PPLX_MODE (default: "pro")
  - PPLX_TEST_FILE (path to file; default uses in-memory text)
  - PPLX_STREAM_VERBOSE (set to "1" to print full payloads)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _print_event(payload: dict, verbose: bool) -> None:
    if verbose:
        print(json.dumps(payload, indent=2))
        return

    if "attachment_processing_progress" in payload:
        print(f"[attachment] {payload['attachment_processing_progress']}")

    status = payload.get("status")
    if status:
        print(f"[status] {status}")

    if payload.get("text_completed"):
        print("[status] text_completed=true")

    if payload.get("answer"):
        print("[answer]")
        print(payload.get("answer", "").strip())


def main() -> int:
    _load_env_file(ROOT / ".env")

    csrf = os.getenv("PPLX_CSRF_TOKEN")
    session = os.getenv("PPLX_SESSION_TOKEN")
    if not csrf or not session:
        print("Missing cookies. Set PPLX_CSRF_TOKEN and PPLX_SESSION_TOKEN.")
        print("Tip: copy .env.example to .env and fill values.")
        return 1

    query = os.getenv("PPLX_QUERY", "Summarize the attached file.")
    mode = os.getenv("PPLX_MODE", "pro")
    file_path = os.getenv("PPLX_TEST_FILE")
    verbose = os.getenv("PPLX_STREAM_VERBOSE") == "1"

    if file_path:
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {path}")
            return 1
        filename = path.name
        data = path.read_bytes()
    else:
        filename = "test.txt"
        data = b"hello world from perplexity integration test"

    print("Using cookies:")
    print(f"  csrf: {_mask(csrf)}")
    print(f"  session: {_mask(session)}")
    print(f"Query: {query}")
    print(f"Mode: {mode}")
    print(f"File: {filename} ({len(data)} bytes)")

    sys.path.insert(0, str(ROOT))
    from perplexity import Client

    cookies = {
        "next-auth.csrf-token": csrf,
        "next-auth.session-token": session,
    }

    try:
        with Client(cookies) as client:
            stream = client.search(
                query,
                mode=mode,
                files={filename: data},
                stream=True,
                wait_for_attachment_processing=True,
            )
            for payload in stream:
                _print_event(payload, verbose)
    except Exception as exc:
        print(f"Test failed: {exc}")
        return 1

    print("Test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
