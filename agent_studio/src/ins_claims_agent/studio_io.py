"""Agent Studio helpers: workflow_data, session artifacts, MCP payload normalize."""

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
    """Point ``INS_CLAIMS_REPO_ROOT`` / ``PACK_ROOT`` at a pack or claims tree."""
    from ins_claims_agent.pack import is_legacy_claims_root, is_pack_root
    from ins_claims_agent.paths import repo_root

    if assets_root:
        root = Path(assets_root).expanduser().resolve()
    else:
        wf = workflow_data_dir()
        if is_pack_root(wf) or is_legacy_claims_root(wf):
            root = wf.resolve()
        else:
            return repo_root()

    if not (is_pack_root(root) or is_legacy_claims_root(root)):
        raise FileNotFoundError(
            f"Assets root missing pack.yaml or ontology/ + playbook/: {root}."
        )
    os.environ["INS_CLAIMS_REPO_ROOT"] = str(root)
    os.environ["PACK_ROOT"] = str(root)
    return root


def graph_artifact_path(claim_id: str | int) -> Path:
    """Session case JSON (legacy name; was Turtle)."""
    return session_dir() / f"claim_{claim_id}_case.json"


def validation_artifact_path(claim_id: str | int) -> Path:
    return session_dir() / f"claim_{claim_id}_validation.json"


def decision_artifact_path(claim_id: str | int) -> Path:
    return session_dir() / f"claim_{claim_id}_route.json"


def letter_artifact_path(claim_id: str | int) -> Path:
    """Session hold/status letter (R1.2 LitigationSupport)."""
    return session_dir() / f"claim_{_safe_claim_id(claim_id)}_letter.txt"


def write_text_artifact(path: Path, text: str) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path.resolve())


def save_claim_letter(
    claim_id: str | int,
    body: str,
    *,
    run_id: str | None = None,
    next_step: str = "LitigationSupport",
) -> dict[str, Any]:
    """Write drafted letter text to SESSION_DIRECTORY. Does not send mail."""
    text = (body or "").strip()
    if not text:
        raise ValueError("body is required (drafted letter text)")
    if not text.endswith("\n"):
        text = text + "\n"
    path = letter_artifact_path(claim_id)
    write_text_artifact(path, text)
    return {
        "claim_id": _safe_claim_id(claim_id),
        "run_id": run_id,
        "next_step": next_step,
        "letter_artifact": str(path.resolve()),
        "session_directory": str(session_dir()),
        "bytes": path.stat().st_size,
    }


def _safe_claim_id(claim_id: str | int) -> str:
    cid = str(claim_id).strip()
    if not cid or any(part in cid for part in ("/", "\\", "..")):
        raise ValueError("claim_id is not a safe artifact name")
    return cid


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


def _lower_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k).lower(): _lower_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_lower_keys(v) for v in obj]
    return obj


def normalize_spine_payload(raw: Any) -> dict[str, Any]:
    """Accept fork MCP envelope or flat spine dict (SQL fallback / tests)."""
    payload = _lower_keys(parse_json_arg(raw, label="spine_json"))
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


def assert_spine_has_triangle_fields(spine: dict[str, Any]) -> None:
    """Fail fast when build would produce a case JSON that validation cannot pass."""
    missing = [
        key
        for key in ("policy_id", "insurable_object_id")
        if spine.get(key) is None or spine.get(key) == ""
    ]
    if missing:
        raise ValueError(
            "spine_json missing required field(s) "
            f"{missing}. Re-call MCP get_claim_spine and pass the full JSON "
            "unmodified into build_claim_graph (do not summarize or omit keys)."
        )


def normalize_signals_payload(raw: Any) -> dict[str, Any]:
    """Accept fork MCP envelope or flat signals dict."""
    payload = _lower_keys(parse_json_arg(raw, label="signals_json"))
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
