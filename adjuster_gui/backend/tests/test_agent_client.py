"""Kickoff payload and routing-summary extraction."""

from __future__ import annotations

import json
import unittest

import httpx

from app.agent_client import answer_from_events, kickoff, next_step_from_answer, process_claim_text


class AgentClientTests(unittest.IsolatedAsyncioTestCase):
    def test_next_step_line(self) -> None:
        text = "Next step: RequestPoliceReport\nLane: PD\n"
        self.assertEqual(next_step_from_answer(text), "RequestPoliceReport")
        self.assertEqual(process_claim_text("401"), "process claim 401")

    async def test_kickoff_sends_process_claim(self) -> None:
        seen: list[tuple[str, dict]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content.decode() or "{}")
            seen.append((request.url.path, body))
            if request.url.path.endswith("createSession"):
                return httpx.Response(200, json={"session_id": "sess-1"})
            if request.url.path.endswith("kickoff"):
                return httpx.Response(200, json={"trace_id": "trace-1"})
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await kickoff(client, "https://workflow.example", "secret", "process claim 401")
        self.assertEqual(result["trace_id"], "trace-1")
        self.assertEqual(result["conversation_id"], "trace-1")
        self.assertEqual(seen[1][1]["inputs"]["user_input"], "process claim 401")
        self.assertEqual(seen[1][1]["inputs"]["context"], "")
        self.assertEqual(seen[0][1], {})

    async def test_kickoff_reads_conversation_id(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("createSession"):
                return httpx.Response(200, json={"session_id": "sess-1"})
            if request.url.path.endswith("kickoff"):
                return httpx.Response(
                    200,
                    json={
                        "success": True,
                        "response": {"trace_id": "trace-9", "conversation_id": "conv-9"},
                    },
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await kickoff(client, "https://workflow.example", "secret", "hello")
        self.assertEqual(result["conversation_id"], "conv-9")
        self.assertEqual(result["trace_id"], "trace-9")

    def test_answer_from_completed_event(self) -> None:
        summary = "Next step: RequestPoliceReport\n\nWhy this routing: No police report on file"
        events = [
            {"type": "tool_call"},
            {
                "type": "crew_kickoff_completed",
                "output": summary,
            },
        ]
        completed, answer, step = answer_from_events(events)
        self.assertTrue(completed)
        self.assertIn("RequestPoliceReport", answer or "")
        self.assertEqual(step, "RequestPoliceReport")

    def test_incomplete_events(self) -> None:
        completed, answer, step = answer_from_events([{"type": "tool_call"}])
        self.assertFalse(completed)
        self.assertIsNone(answer)
        self.assertIsNone(step)
