"""Optional pack fixture catalog (demo packs without Impala tables)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def pack_root() -> Path | None:
    raw = os.getenv("PACK_ROOT") or os.getenv("INS_CLAIMS_REPO_ROOT")
    if not raw:
        return None
    root = Path(raw).expanduser().resolve()
    if (root / "catalog_fixtures.json").is_file() or (root / "pack.yaml").is_file():
        return root
    return None


def merge_pack_catalog(
    read_ops: dict[str, dict[str, Any]],
    write_ops: dict[str, dict[str, Any]],
) -> str | None:
    root = pack_root()
    if root is None:
        return None
    fixture_file = root / "catalog_fixtures.json"
    if not fixture_file.is_file():
        return None
    raw = json.loads(fixture_file.read_text(encoding="utf-8"))
    for label, spec in (raw.get("reads") or {}).items():
        fixture_rel = spec.get("fixture_dir")
        if not fixture_rel:
            continue
        fixture_dir = root / fixture_rel
        read_ops[label] = {
            "required": tuple(spec.get("required") or ("claim_id",)),
            "optional": tuple(spec.get("optional") or ("database", "case_id")),
            "summary": spec.get("summary") or f"Pack fixture {label}",
            "handler": _fixture_read_handler(fixture_dir, label),
        }
    if raw.get("fixture_writes"):
        write_ops["write_audit_event"] = {
            "required": ("run_id", "event_json"),
            "optional": ("database",),
            "summary": "Fixture audit write (no Impala)",
            "handler": _fixture_write_handler("write_audit_event"),
        }
        write_ops["promote_audit_run"] = {
            "required": ("run_id",),
            "optional": ("database",),
            "summary": "Fixture promote (no Impala)",
            "handler": _fixture_write_handler("promote_audit_run"),
        }
    return str(raw.get("id") or root.name)


def _fixture_read_handler(fixture_dir: Path, label: str):
    def handler(params: dict[str, Any]) -> str:
        cid = str(params.get("claim_id") or params.get("case_id") or "").strip()
        path = fixture_dir / f"{cid}.json"
        if not path.is_file():
            return json.dumps(
                {
                    "error": True,
                    "message": "no fixture for case",
                    "label": label,
                    "case_id": cid,
                    "fixture_dir": str(fixture_dir),
                }
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload.setdefault("case_id", cid)
            payload.setdefault("claim_id", cid)
            payload.setdefault("fixture", True)
        return json.dumps(payload, default=str)

    return handler


def _fixture_write_handler(label: str):
    def handler(params: dict[str, Any]) -> str:
        return json.dumps(
            {
                "ok": True,
                "fixture": True,
                "run_id": params.get("run_id"),
                "named_op": label,
                "mode": "fixture",
                "note": "PACK_ROOT fixture write; no Impala INSERT.",
            }
        )

    return handler
