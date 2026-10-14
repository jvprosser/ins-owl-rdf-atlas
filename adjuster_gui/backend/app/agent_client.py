"""Proxy the Agent Studio workflow calls used by the adjuster GUI.

Deployed workflow calls: kickoff, then events.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import httpx

KICKOFF_PATH = "/api/workflow/kickoff"
EVENTS_PATH = "/api/workflow/events"
_COMPLETED_TYPES = frozenset(
    {
        "crew_kickoff_completed",
        "crew_kickoff_complete",
        "Crew.complete",
    }
)
_NEXT_STEP = re.compile(r"Next step:\s*([A-Za-z0-9_.-]+)")


def ssl_verify() -> bool:
    return os.environ.get("ADJUSTER_GUI_SSL_VERIFY", "false").lower() in {
        "1",
        "true",
        "yes",
    }


def workflow_headers(token: str, *, json_body: bool = True) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def process_claim_text(claim_id: str) -> str:
    return f"process claim {str(claim_id).strip()}"


def next_step_from_answer(text: str) -> Optional[str]:
    match = _NEXT_STEP.search(text or "")
    if not match:
        return None
    return match.group(1)


def _parse_event_line(line: str) -> Any | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(":"):
        return None
    if stripped.startswith("data:"):
        stripped = stripped[5:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def parse_events_payload(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("events", "workflow_events", "data"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return nested
        return [payload]
    return [payload]


def _find_completed(events: list[Any]) -> dict[str, Any] | None:
    for event in reversed(events):
        if isinstance(event, dict) and event.get("type") in _COMPLETED_TYPES:
            return event
    return None


def _looks_like_html(raw: str, content_type: str) -> bool:
    if "html" in content_type.lower():
        return True
    stripped = raw.lstrip().lower()
    return stripped.startswith("<!doctype") or stripped.startswith("<html")


def _strings(value: Any, *, depth: int = 0) -> list[str]:
    if value is None or depth > 8:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        found: list[str] = []
        for nested in value.values():
            found.extend(_strings(nested, depth=depth + 1))
        return found
    if isinstance(value, list):
        found = []
        for item in value:
            found.extend(_strings(item, depth=depth + 1))
        return found
    return []


_OUTPUT_KEYS = frozenset(
    {"output", "result", "content", "message", "text", "answer", "raw", "final_output"}
)


def response_texts(events: list[Any]) -> list[str]:
    """Agent-visible strings from workflow events, in arrival order."""
    found: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        cleaned = text.strip()
        if len(cleaned) < 2 or cleaned in seen or _looks_like_html(cleaned, ""):
            return
        seen.add(cleaned)
        found.append(cleaned)

    def walk(value: Any, *, emit: bool, depth: int) -> None:
        if value is None or depth > 8:
            return
        if isinstance(value, str):
            if emit:
                add(value)
            return
        if isinstance(value, dict):
            for key, nested in value.items():
                walk(nested, emit=emit or key in _OUTPUT_KEYS, depth=depth + 1)
            return
        if isinstance(value, list):
            for item in value:
                walk(item, emit=emit, depth=depth + 1)

    for event in events:
        walk(event, emit=False, depth=0)
    return found


def answer_from_events(events: list[Any]) -> tuple[bool, Optional[str], Optional[str]]:
    """Return (completed, markdown, next_step)."""
    completed = _find_completed(events)
    if completed is None:
        return False, None, None
    texts = _strings(completed)
    with_step = [text for text in texts if next_step_from_answer(text)]
    if with_step:
        answer = max(with_step, key=len)
    else:
        long_enough = [text for text in texts if len(text) > 20]
        answer = max(long_enough, key=len) if long_enough else (texts[-1] if texts else "")
    return True, answer, next_step_from_answer(answer or "")


def _json_body(response: httpx.Response, path: str, raw: str | None = None) -> Any:
    body = response.text if raw is None else raw
    if _looks_like_html(body, response.headers.get("content-type", "")):
        raise ValueError(
            f"{path} returned the workflow web page (HTTP {response.status_code}) instead of JSON. "
            "Use the deployed workflow application URL, with no extra path."
        )
    response.raise_for_status()
    try:
        return json.loads(body) if body.strip() else None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Workflow {path} did not return JSON") from exc


async def _post_json(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    token: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = await client.post(
        f"{base_url.rstrip('/')}{path}",
        headers=workflow_headers(token),
        json=payload,
    )
    parsed = _json_body(response, path)
    if not isinstance(parsed, dict):
        raise ValueError(f"Unexpected JSON from {path}")
    return parsed


def _field(payload: dict[str, Any], key: str) -> Optional[str]:
    value = payload.get(key)
    if value not in (None, ""):
        return str(value)
    nested = payload.get("response")
    if isinstance(nested, dict):
        value = nested.get(key)
        if value not in (None, ""):
            return str(value)
    return None


async def kickoff(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    user_input: str,
) -> dict[str, str]:
    started = await _post_json(
        client,
        base_url,
        KICKOFF_PATH,
        token,
        {
            "inputs": {
                "user_input": user_input,
                "context": "",
            }
        },
    )
    if started.get("success") is False:
        detail = started.get("error") or started.get("message") or "kickoff failed"
        raise ValueError(str(detail))
    trace_id = _field(started, "trace_id")
    conversation_id = _field(started, "conversation_id") or trace_id
    if not conversation_id:
        raise ValueError("kickoff response missing conversation_id")
    return {
        "session_id": "",
        "trace_id": trace_id or conversation_id,
        "conversation_id": conversation_id,
    }


async def fetch_events(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    conversation_id: str,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{EVENTS_PATH}"
    async with client.stream(
        "GET",
        url,
        headers=workflow_headers(token, json_body=False),
        params={"trace_id": conversation_id, "conversation_id": conversation_id},
    ) as response:
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            response.raise_for_status()
            events: list[Any] = []
            async for line in response.aiter_lines():
                parsed = _parse_event_line(line)
                if parsed is not None:
                    events.append(parsed)
        else:
            raw = (await response.aread()).decode("utf-8", errors="replace")
            parsed_body = _json_body(response, EVENTS_PATH, raw)
            events = [] if parsed_body is None else parse_events_payload(parsed_body)
    completed, answer, step = answer_from_events(events)
    return {
        "trace_id": conversation_id,
        "conversation_id": conversation_id,
        "completed": completed,
        "answer": answer,
        "next_step": step,
        "responses": response_texts(events),
    }
