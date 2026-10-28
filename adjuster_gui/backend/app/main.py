"""Claims Copilot API: BPMN assets plus a proxy to the Agent Studio workflow."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent_client
from .bpmn_layout import write_positions

GUI_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = GUI_ROOT / "frontend" / "dist"
# CML sets CDSW_APP_PORT for Applications; default to 8010 for local dev
# (the Process Mapper uses 8000). On CML, bind 127.0.0.1 — that is the address
# the platform proxy connects to. Binding 0.0.0.0 fails when the engine already
# holds that port on another address.
APP_HOST = os.environ.get("APP_HOST") or (
    "127.0.0.1" if os.environ.get("CDSW_APP_PORT") else "0.0.0.0"
)
APP_PORT = int(os.environ.get("CDSW_APP_PORT", os.environ.get("ADJUSTER_GUI_PORT", "8010")))
# Uvicorn subprocess handle. Lives on this imported module so a CML kernel
# re-run of backend/main.py still sees the server it already started.
_server_proc = None

app = FastAPI(title="Claims Copilot", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class KickoffRequest(BaseModel):
    base_url: str
    token: str
    user_input: str = ""
    claim_id: str = ""
    workflow_id: str = ""


class ShapePosition(BaseModel):
    x: float
    y: float


class BpmnLayoutRequest(BaseModel):
    positions: dict[str, ShapePosition]


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=120.0, verify=agent_client.ssl_verify())


def _stream_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(300.0, connect=30.0),
        verify=agent_client.ssl_verify(),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "adjuster-gui"}


@app.get("/claims.json")
def claims_file() -> FileResponse:
    path = GUI_ROOT / "claims.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="claims.json is missing")
    return FileResponse(path)


def _sample_bpmn_path() -> Path:
    return GUI_ROOT / "sample" / "claims_playbook.bpmn"


@app.get("/sample/claims_playbook.bpmn")
def sample_bpmn() -> FileResponse:
    path = _sample_bpmn_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="sample BPMN is missing")
    return FileResponse(path, media_type="application/xml")


@app.post("/sample/claims_playbook.bpmn")
def save_sample_bpmn(body: BpmnLayoutRequest) -> dict[str, int]:
    path = _sample_bpmn_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="sample BPMN is missing")
    positions = {node_id: (pos.x, pos.y) for node_id, pos in body.positions.items()}
    try:
        count = write_positions(path, positions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"updated": count}


@app.post("/api/agent/kickoff")
async def agent_kickoff(body: KickoffRequest) -> dict[str, str]:
    if not body.base_url.strip() or not body.token.strip():
        raise HTTPException(status_code=400, detail="Workflow URL and bearer token are required.")
    user_input = body.user_input.strip()
    if not user_input and body.claim_id.strip():
        user_input = agent_client.process_claim_text(body.claim_id)
    if not user_input:
        raise HTTPException(status_code=400, detail="A message is required.")
    try:
        async with _client() as client:
            return await agent_client.kickoff(
                client,
                body.base_url.strip(),
                body.token.strip(),
                user_input,
                body.workflow_id,
            )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] or str(exc)
        raise HTTPException(status_code=502, detail=detail) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/agent/events/stream")
async def agent_events_stream(
    base_url: str = Query(...),
    token: str = Header(..., alias="X-Workflow-Token"),
    conversation_id: str = Query(""),
    trace_id: str = Query(""),
) -> StreamingResponse:
    poll_id = (trace_id or conversation_id).strip()
    if not base_url.strip() or not token.strip() or not poll_id:
        raise HTTPException(
            status_code=400, detail="base_url, token, and trace_id are required."
        )

    async def generate():
        try:
            async with _stream_client() as client:
                async for update in agent_client.iter_events(
                    client, base_url.strip(), token.strip(), poll_id
                ):
                    yield json.dumps(update) + "\n"
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] or str(exc)
            yield json.dumps({"error": detail}) + "\n"
        except (httpx.RequestError, ValueError) as exc:
            yield json.dumps({"error": str(exc)}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/agent/events")
async def agent_events(
    base_url: str = Query(...),
    token: str = Header(..., alias="X-Workflow-Token"),
    conversation_id: str = Query(""),
    trace_id: str = Query(""),
) -> dict:
    poll_id = (conversation_id or trace_id).strip()
    if not base_url.strip() or not token.strip() or not poll_id:
        raise HTTPException(
            status_code=400, detail="base_url, token, and conversation_id are required."
        )
    try:
        async with _client() as client:
            return await agent_client.fetch_events(
                client, base_url.strip(), token.strip(), poll_id
            )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] or str(exc)
        raise HTTPException(status_code=502, detail=detail) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
