"""Adjuster GUI API: BPMN assets plus a proxy to the Agent Studio workflow."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import agent_client

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

app = FastAPI(title="Adjuster BPMN GUI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class KickoffRequest(BaseModel):
    base_url: str
    token: str
    claim_id: str = Field(min_length=1)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=120.0, verify=agent_client.ssl_verify())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "adjuster-gui"}


@app.get("/claims.json")
def claims_file() -> FileResponse:
    path = GUI_ROOT / "claims.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="claims.json is missing")
    return FileResponse(path)


@app.get("/sample/claims_playbook.bpmn")
def sample_bpmn() -> FileResponse:
    path = GUI_ROOT / "sample" / "claims_playbook.bpmn"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="sample BPMN is missing")
    return FileResponse(path, media_type="application/xml")


@app.post("/api/agent/kickoff")
async def agent_kickoff(body: KickoffRequest) -> dict[str, str]:
    if not body.base_url.strip() or not body.token.strip():
        raise HTTPException(status_code=400, detail="Workflow URL and bearer token are required.")
    try:
        async with _client() as client:
            return await agent_client.kickoff(
                client, body.base_url.strip(), body.token.strip(), body.claim_id.strip()
            )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] or str(exc)
        raise HTTPException(status_code=502, detail=detail) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/agent/events")
async def agent_events(
    base_url: str = Query(...),
    trace_id: str = Query(...),
    token: str = Header(..., alias="X-Workflow-Token"),
) -> dict:
    if not base_url.strip() or not token.strip() or not trace_id.strip():
        raise HTTPException(status_code=400, detail="base_url, token, and trace_id are required.")
    try:
        async with _client() as client:
            return await agent_client.fetch_events(
                client, base_url.strip(), token.strip(), trace_id.strip()
            )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] or str(exc)
        raise HTTPException(status_code=502, detail=detail) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
