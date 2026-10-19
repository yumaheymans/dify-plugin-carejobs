"""Small client for the CareJobs.Now remote MCP server.

The server is public, free and read-only: no API key, no account. Every Dify tool in this
plugin makes exactly one JSON-RPC `tools/call` request to the single fixed endpoint below.
The destination is not configurable, there are no redirects, no retries, and no data is
written anywhere.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

import requests

ENDPOINT = "https://carejobs.now/api/mcp"
USER_AGENT = "dify-plugin-carejobs (+https://carejobs.now)"
CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_TEXT_ARGUMENT_CHARS = 200


class CareJobsError(Exception):
    """The CareJobs.Now service could not answer, or rejected the request."""


@dataclass(frozen=True)
class ToolResult:
    """A successful tool answer: a readable summary and, when present, structured data."""

    text: str
    data: dict[str, Any] | None


def build_arguments(
    tool_parameters: Mapping[str, Any], spec: Mapping[str, Any]
) -> dict[str, Any]:
    """Turn Dify tool parameters into the argument object of an MCP tool call.

    `spec` maps a parameter name to "string", "boolean" or ("integer", minimum, maximum).
    Empty values are dropped so the server applies its own defaults. Integers are clamped
    into their range, and over-long text is rejected rather than sent.
    """
    arguments: dict[str, Any] = {}
    for name, kind in spec.items():
        value = tool_parameters.get(name)
        if value is None:
            continue
        if kind == "string":
            text = str(value).strip()
            if not text:
                continue
            if len(text) > MAX_TEXT_ARGUMENT_CHARS:
                raise CareJobsError(
                    f"'{name}' is too long ({len(text)} characters, at most "
                    f"{MAX_TEXT_ARGUMENT_CHARS})."
                )
            arguments[name] = text
        elif kind == "boolean":
            flag = value.strip().lower() == "true" if isinstance(value, str) else bool(value)
            if flag:
                arguments[name] = True
        else:
            _, minimum, maximum = kind
            if isinstance(value, str) and not value.strip():
                continue
            try:
                number = int(float(value))
            except (TypeError, ValueError):
                raise CareJobsError(f"'{name}' must be a whole number.") from None
            arguments[name] = max(minimum, min(maximum, number))
    return arguments


def call_tool(name: str, arguments: Mapping[str, Any]) -> ToolResult:
    """Call one CareJobs.Now MCP tool and return its summary and structured data."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": dict(arguments)},
    }
    try:
        response = requests.post(
            ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": USER_AGENT,
            },
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            allow_redirects=False,
            stream=True,
        )
    except requests.RequestException as exc:
        raise CareJobsError(f"Could not reach CareJobs.Now ({type(exc).__name__}).") from None

    with response:
        if response.status_code != 200:
            raise CareJobsError(f"CareJobs.Now answered HTTP {response.status_code}.")
        body = _read_capped(response)
        content_type = response.headers.get("Content-Type", "")

    message = _parse_message(body, content_type)
    if "error" in message:
        detail = message["error"]
        text = detail.get("message") if isinstance(detail, dict) else str(detail)
        raise CareJobsError(f"CareJobs.Now rejected the request: {text}")

    result = message.get("result")
    if not isinstance(result, dict):
        raise CareJobsError("CareJobs.Now returned an answer this plugin cannot read.")

    text = _result_text(result)
    if result.get("isError"):
        raise CareJobsError(text or "CareJobs.Now could not answer this request.")

    structured = result.get("structuredContent")
    data = structured if isinstance(structured, dict) else None
    return ToolResult(text=text, data=data)


def _read_capped(response: requests.Response) -> bytes:
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_content(chunk_size=65536):
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise CareJobsError("CareJobs.Now returned an unexpectedly large answer.")
        chunks.append(chunk)
    return b"".join(chunks)


def _parse_message(body: bytes, content_type: str) -> dict[str, Any]:
    """Read the JSON-RPC message from a plain JSON body or a server-sent-events body."""
    text = body.decode("utf-8", errors="replace")
    try:
        if "text/event-stream" in content_type:
            events = [
                line[5:].strip() for line in text.splitlines() if line.startswith("data:")
            ]
            parsed = json.loads(events[-1]) if events else None
        else:
            parsed = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        parsed = None
    if not isinstance(parsed, dict):
        raise CareJobsError("CareJobs.Now returned an answer this plugin cannot read.")
    return parsed


def _result_text(result: Mapping[str, Any]) -> str:
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    parts = [
        item["text"]
        for item in content
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)
    ]
    return "\n".join(parts).strip()
