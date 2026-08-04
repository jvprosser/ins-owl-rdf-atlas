"""Agent Studio Path A helpers: workflow_data, session artifacts, MCP payload normalize."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def workflow_data_dir() -> Path:
    return Path(os.environ.get("WORKFLOW_DATA_DIRECTORY", "/workflow_data")).expanduser()


def session_dir() -> Path:
    return Path(os.environ.get("SESSION_DIRECTORY", os.getcwd())).expanduser()


def configure_workflow_assets(assets_root: str | None = None) -> Path:
    """Point ``INS_CLAIMS_REPO_ROOT`` at ontology/probes/playbook.

    Prefer explicit ``assets_root``, else ``WORKFLOW_DATA_DIRECTORY``, else leave
    path discovery to ``ins_claims_agent.paths`` (repo walk-up / existing env).
    """
    if assets_root:
        root = Path(assets_root).expanduser().resolve()
    else:
        wf = workflow_data_dir()
        if (wf / "ontology" / "claims_mvt.ttl").is_file() and (
            wf / "playbook" / "playbook.yaml"
        ).is_file():
            root = wf.resolve()
        else:
            # Local/dev: paths.py walk-up / INS_CLAIMS_REPO_ROOT already set
            from ins_claims_agent.paths import repo_root

            return repo_root()

    if not (root / "ontology" / "claims_mvt.ttl").is_file():
        raise FileNotFoundError(
            f"Assets root missing ontology/claims_mvt.ttl: {root}. "
            "Copy ontology/, probes/, playbook/ into WORKFLOW_DATA_DIRECTORY."
        )
    if not (root / "playbook" / "playbook.yaml").is_file():
        raise FileNotFoundError(
            f"Assets root missing playbook/playbook.yaml: {root}."
        )
    os.environ["INS_CLAIMS_REPO_ROOT"] = str(root)
    return root


def graph_artifact_path(claim_id: str | int) -> Path:
    return session_dir() / f"claim_{claim_id}_graph.ttl"


def validation_artifact_path(claim_id: str | int) -> Path:
    return session_dir() / f"claim_{claim_id}_validation.json"


def decision_artifact_path(claim_id: str | int) -> Path:
    return session_dir() / f"claim_{claim_id}_route.json"


def write_json_artifact(path: Path, data: Any) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return str(path.resolve())


def parse_json_arg(raw: Any, *, label: str = "json") -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    if raw is None:
        return {}
    if not isinstance(raw, str):
        raise ValueError(f"{label} must be a JSON string or object")
    text = raw.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc


def normalize_spine_payload(raw: Any) -> dict[str, Any]:
    """Accept fork MCP envelope or flat spine dict (SQL fallback / tests)."""
    payload = parse_json_arg(raw, label="spine_json")
    if not isinstance(payload, dict):
        raise ValueError("spine_json must be a JSON object")
    if payload.get("error") and "spine" not in payload:
        raise ValueError(str(payload["error"]))
    if isinstance(payload.get("spine"), dict):
        spine = dict(payload["spine"])
        if "roles" not in spine:
            spine["roles"] = list(payload.get("roles") or [])
        if "claim_id" not in spine and payload.get("claim_id") is not None:
            spine["claim_id"] = payload["claim_id"]
        return spine
    return payload


def normalize_signals_payload(raw: Any) -> dict[str, Any]:
    """Accept fork MCP envelope or flat signals dict."""
    payload = parse_json_arg(raw, label="signals_json")
    if not isinstance(payload, dict):
        raise ValueError("signals_json must be a JSON object")
    if payload.get("error") and "signals" not in payload:
        raise ValueError(str(payload["error"]))
    if isinstance(payload.get("signals"), dict):
        out = dict(payload["signals"])
        for key in (
            "injury_ids",
            "offers",
            "payment_ids",
            "recovery_ids",
            "document_ids",
        ):
            if key in payload and key not in out:
                out[key] = payload[key]
        return out
    return payload
