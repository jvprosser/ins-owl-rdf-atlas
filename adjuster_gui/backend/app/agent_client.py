"""Proxy the Agent Studio workflow calls used by the adjuster GUI.

Deployed workflow calls: createSession, kickoff, then events.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from collections.abc import AsyncIterator
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

import httpx

_CREATE_SESSION_PATH = "/api/workflow/createSession"
_KICKOFF_PATHS = ("/api/workflow/kickoff", "/api/workflow")
_EVENT_PATHS = ("/api/workflow/events", "/api/workflow")
# Studio's own Test action. /api/workflow/kickoff is only for a deployed workflow app.
_TEST_WORKFLOW_PATH = "/api/grpc/testWorkflow"
_COMPLETED_TYPES = frozenset(
    {
        "crew_kickoff_completed",
        "crew_kickoff_complete",
        "crew_kickoff_failed",
        "Crew.complete",
    }
)
# The events route drains a queue. An immediate read is often empty.
_EVENT_POLL_INTERVAL_S = 1.0
_EVENT_POLL_TIMEOUT_S = 300.0
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


def workflow_cookies(token: str) -> dict[str, str]:
    """Workbench session cookie. Studio reads this when Authorization alone has no role."""
    return {"_cdswuserstoken": token}


def use_workflow_token(client: httpx.AsyncClient, token: str) -> None:
    client.cookies.update(workflow_cookies(token))


class _WorkflowPage(ValueError):
    def __init__(self, path: str, status: int) -> None:
        self.status = status
        super().__init__(
            f"{path} returned the workflow web page (HTTP {status}) instead of JSON. "
            "Use the deployed workflow application URL, with no extra path."
        )


def _is_studio_application(origin: str) -> bool:
    """Agent Studio application host, as opposed to a deployed workflow app."""
    host = (urlsplit(origin).hostname or "").lower()
    return host.startswith("cai-agent-studio")


def application_origin(base_url: str) -> str:
    """Scheme and host only. A pasted page path makes /api/workflow 404 as HTML."""
    parts = urlsplit(base_url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("Workflow URL must start with http:// or https://.")
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


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
    {
        "output",
        "outout",
        "result",
        "content",
        "message",
        "text",
        "answer",
        "raw",
        "final_output",
    }
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
        raise _WorkflowPage(path, response.status_code)
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


async def _post_workflow(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    paths: tuple[str, ...],
    payload: dict[str, Any],
) -> dict[str, Any]:
    origin = application_origin(base_url)
    last_error: Optional[Exception] = None
    for index, path in enumerate(paths):
        try:
            return await _post_json(client, origin, path, token, payload)
        except _WorkflowPage as exc:
            last_error = exc
            if exc.status not in (404, 405):
                raise
        except httpx.HTTPStatusError as exc:
            # A GET-only catch-all answers unknown POSTs with 405, not 404.
            if exc.response.status_code == 405 and index < len(paths) - 1:
                last_error = exc
                continue
            raise
    if last_error is not None:
        raise last_error
    raise ValueError("Workflow kickoff was not sent.")


async def _deployed_session_id(
    client: httpx.AsyncClient,
    origin: str,
    token: str,
) -> str:
    """Create the session a deployed workflow app requires before kickoff."""
    try:
        session = await _post_json(client, origin, _CREATE_SESSION_PATH, token, {})
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (404, 405):
            return ""
        raise
    except _WorkflowPage as exc:
        if exc.status in (404, 405):
            return ""
        raise
    if session.get("success") is False:
        detail = session.get("error") or session.get("message") or "createSession failed"
        raise ValueError(str(detail))
    if session.get("error"):
        raise ValueError(str(session.get("error")))
    found = session.get("session_id") or _field(session, "session_id")
    return str(found) if found else ""


async def _session_id(
    client: httpx.AsyncClient,
    origin: str,
    token: str,
    workflow_id: str,
) -> str:
    try:
        session = await _post_json(
            client,
            origin,
            _CREATE_SESSION_PATH,
            token,
            {"workflow_id": workflow_id},
        )
    except _WorkflowPage as exc:
        if exc.status == 404:
            return ""
        raise
    if session.get("success") is False:
        detail = session.get("error") or session.get("message") or "createSession failed"
        raise ValueError(str(detail))
    if session.get("error"):
        raise ValueError(str(session.get("error")))
    found = session.get("session_id") or _field(session, "session_id")
    return str(found) if found else ""


async def _studio_test(
    client: httpx.AsyncClient,
    origin: str,
    token: str,
    user_input: str,
    workflow_id: str,
) -> dict[str, str]:
    """Start a run the way Studio's Test button does.

    testWorkflow accepts an empty session_id. A token without session:create
    still gets that far.
    """
    try:
        session_id = await _session_id(client, origin, token, workflow_id)
    except (httpx.HTTPStatusError, ValueError, _WorkflowPage):
        session_id = ""
    started = await _post_json(
        client,
        origin,
        _TEST_WORKFLOW_PATH,
        token,
        {
            "workflow_id": workflow_id,
            "inputs": {
                "user_input": user_input,
                "context": "",
            },
            "tool_user_parameters": {},
            "mcp_instance_env_vars": {},
            "generation_config": "{}",
            "session_id": session_id,
        },
    )
    trace_id, conversation_id = _trace_ids(started)
    return {
        "session_id": session_id,
        "trace_id": trace_id,
        "conversation_id": conversation_id,
    }


def _trace_ids(started: dict[str, Any]) -> tuple[str, str]:
    if started.get("success") is False:
        detail = started.get("error") or started.get("message") or "kickoff failed"
        raise ValueError(str(detail))
    trace_id = _field(started, "trace_id")
    conversation_id = _field(started, "conversation_id") or trace_id
    if not conversation_id:
        raise ValueError("kickoff response missing conversation_id")
    return trace_id or conversation_id, conversation_id


async def kickoff(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    user_input: str,
    workflow_id: str = "",
) -> dict[str, str]:
    origin = application_origin(base_url)
    use_workflow_token(client, token)
    workflow_id = workflow_id.strip()
    if workflow_id and _is_studio_application(origin):
        return await _studio_test(client, origin, token, user_input, workflow_id)
    session_id = await _deployed_session_id(client, origin, token)
    payload: dict[str, Any] = {
        "inputs": {
            "user_input": user_input,
            "context": "",
        }
    }
    if session_id:
        payload["session_id"] = session_id
    started = await _post_workflow(
        client,
        origin,
        token,
        _KICKOFF_PATHS,
        payload,
    )
    trace_id, conversation_id = _trace_ids(started)
    return {
        "session_id": session_id,
        "trace_id": trace_id,
        "conversation_id": conversation_id,
    }


async def _fetch_events_at(
    client: httpx.AsyncClient,
    origin: str,
    token: str,
    conversation_id: str,
    path: str,
) -> dict[str, Any]:
    url = f"{origin}{path}"
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
            parsed_body = _json_body(response, path, raw)
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


def _event_update(events: list[Any]) -> dict[str, Any]:
    completed, answer, step = answer_from_events(events)
    return {
        "completed": completed,
        "answer": answer,
        "next_step": step,
        "responses": response_texts(events),
    }


async def _iter_events_at(
    client: httpx.AsyncClient,
    origin: str,
    token: str,
    trace_id: str,
    path: str,
) -> AsyncIterator[dict[str, Any]]:
    url = f"{origin}{path}"
    async with client.stream(
        "GET",
        url,
        headers=workflow_headers(token, json_body=False),
        params={"trace_id": trace_id},
    ) as response:
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            response.raise_for_status()
            async for line in response.aiter_lines():
                parsed = _parse_event_line(line)
                if parsed is None:
                    continue
                batch = parsed if isinstance(parsed, list) else [parsed]
                update = _event_update(batch)
                if update["responses"] or update["completed"]:
                    yield update
            return
        raw = (await response.aread()).decode("utf-8", errors="replace")
    deadline = time.monotonic() + _EVENT_POLL_TIMEOUT_S
    seen: list[str] = []
    accumulated: list[Any] = []
    while True:
        if raw is None:
            response = await client.get(
                url,
                headers=workflow_headers(token, json_body=False),
                params={"trace_id": trace_id},
            )
            raw = response.text
        parsed_body = _json_body(response, path, raw)
        raw = None
        events = [] if parsed_body is None else parse_events_payload(parsed_body)
        if events:
            accumulated.extend(events)
            update = _event_update(accumulated)
            fresh = [text for text in update["responses"] if text not in seen]
            seen.extend(fresh)
            if fresh or update["completed"]:
                update["responses"] = fresh
                yield update
            if update["completed"]:
                return
        if time.monotonic() >= deadline:
            raise ValueError("The workflow did not finish in time.")
        await asyncio.sleep(_EVENT_POLL_INTERVAL_S)


async def iter_events(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    trace_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Yield each workflow event as it arrives on the trace stream."""
    use_workflow_token(client, token)
    origin = application_origin(base_url)
    last_page: Optional[_WorkflowPage] = None
    for path in _EVENT_PATHS:
        try:
            async for update in _iter_events_at(client, origin, token, trace_id, path):
                yield update
            return
        except _WorkflowPage as exc:
            last_page = exc
            if exc.status != 404:
                raise
    if last_page is not None:
        raise last_page
    raise ValueError("Workflow events were not requested.")


async def fetch_events(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    conversation_id: str,
) -> dict[str, Any]:
    use_workflow_token(client, token)
    origin = application_origin(base_url)
    last_page: Optional[_WorkflowPage] = None
    for path in _EVENT_PATHS:
        try:
            return await _fetch_events_at(client, origin, token, conversation_id, path)
        except _WorkflowPage as exc:
            last_page = exc
            if exc.status != 404:
                raise
    if last_page is not None:
        raise last_page
    raise ValueError("Workflow events were not requested.")
