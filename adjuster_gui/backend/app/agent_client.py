"""Proxy the Agent Studio workflow calls used by the adjuster GUI.

Same three calls as AgenticBPM: createSession, kickoff, events.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import httpx

CREATE_SESSION_PATH = "/api/workflow/createSession"
KICKOFF_PATH = "/api/workflow/kickoff"
EVENTS_PATH = "/api/workflow/events"
CREW_KICKOFF_COMPLETED = "crew_kickoff_completed"
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
        if isinstance(event, dict) and event.get("type") == CREW_KICKOFF_COMPLETED:
            return event
    return None


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
    response.raise_for_status()
    parsed = response.json()
    if not isinstance(parsed, dict):
        raise ValueError(f"Unexpected JSON from {path}")
    return parsed


async def kickoff(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    claim_id: str,
) -> dict[str, str]:
    session = await _post_json(client, base_url, CREATE_SESSION_PATH, token, {})
    session_id = session.get("session_id")
    if not session_id:
        raise ValueError("createSession response missing session_id")
    started = await _post_json(
        client,
        base_url,
        KICKOFF_PATH,
        token,
        {
            "inputs": {
                "user_input": process_claim_text(claim_id),
                "context": "",
            }
        },
    )
    trace_id = started.get("trace_id")
    if not trace_id:
        raise ValueError("kickoff response missing trace_id")
    return {"session_id": str(session_id), "trace_id": str(trace_id)}


async def fetch_events(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    trace_id: str,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{EVENTS_PATH}"
    async with client.stream(
        "GET",
        url,
        headers=workflow_headers(token, json_body=False),
        params={"trace_id": trace_id},
    ) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            events: list[Any] = []
            async for line in response.aiter_lines():
                parsed = _parse_event_line(line)
                if parsed is not None:
                    events.append(parsed)
        else:
            raw = (await response.aread()).decode("utf-8", errors="replace").strip()
            if not raw:
                events = []
            else:
                try:
                    events = parse_events_payload(json.loads(raw))
                except json.JSONDecodeError:
                    events = [
                        parsed
                        for line in raw.splitlines()
                        if (parsed := _parse_event_line(line)) is not None
                    ]
    completed, answer, step = answer_from_events(events)
    return {
        "trace_id": trace_id,
        "completed": completed,
        "answer": answer,
        "next_step": step,
    }
