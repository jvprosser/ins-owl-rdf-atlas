"""Unstructured NL pre-router: cosine match, LLM fallback flag, structured-intake authority."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ins_claims_agent.pre_router.cosine import TfidfIndex, build_index, cosine_search

# Coarse triage only. Structured claim intake (YAML probes + playbook) remains
# authoritative for claim_id.
LABELS = ("LITIGATION", "GENERAL_CLAIMS")
DEFAULT_THRESHOLD = 0.28
DEFAULT_MARGIN = 0.04
CONTENT_ID = "INS_CLAIMS_PRE_ROUTE_V2"

DISPATCH = {
    "LITIGATION": {
        "coworker": "Litigation Agent",
        "agent_role": "LitigationAgent",
        "next_step": "LitigationSupport",
        "lane": "LITIGATION",
    },
    "GENERAL_CLAIMS": {
        "coworker": "Manager agent",
        "agent_role": "ManagerAgent",
        "next_step": "StructuredIntake",
        "lane": "CLAIMS",
    },
}

_PKG_EXEMPLARS = Path(__file__).resolve().parent / "exemplars.yaml"


def _exemplars_path(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("INS_CLAIMS_PRE_ROUTER_EXEMPLARS")
    if env:
        return Path(env).expanduser().resolve()
    for key in ("PACK_ROOT", "INS_CLAIMS_REPO_ROOT"):
        pack_env = os.environ.get(key)
        if pack_env:
            for rel in ("exemplars.yaml", "pre_router/exemplars.yaml"):
                candidate = Path(pack_env).expanduser() / rel
                if candidate.is_file():
                    return candidate.resolve()
    wf = os.environ.get("WORKFLOW_DATA_DIRECTORY")
    if wf:
        for rel in ("exemplars.yaml", "pre_router/exemplars.yaml"):
            candidate = Path(wf).expanduser() / rel
            if candidate.is_file():
                return candidate.resolve()
    return _PKG_EXEMPLARS


def load_catalog(path: str | Path | None = None) -> dict[str, Any]:
    catalog_path = _exemplars_path(path)
    if not catalog_path.is_file():
        raise FileNotFoundError(f"pre-router exemplars not found: {catalog_path}")
    with catalog_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    exemplars = list(data.get("exemplars") or [])
    if not exemplars:
        raise ValueError(f"no exemplars in {catalog_path}")
    allowed = tuple(data.get("labels") or LABELS)
    for row in exemplars:
        label = str(row.get("label") or "")
        if label not in allowed:
            raise ValueError(f"unknown exemplar label {label!r} in {catalog_path}")
        if not str(row.get("text") or "").strip():
            raise ValueError(f"empty exemplar text id={row.get('id')!r}")
    return {
        "path": str(catalog_path),
        "catalog_version": int(data.get("catalog_version") or 1),
        "labels": list(data.get("labels") or LABELS),
        "dispatch": data.get("dispatch") or DISPATCH,
        "exemplars": exemplars,
    }


@lru_cache(maxsize=4)
def _cached_index(path_str: str, mtime_ns: int) -> TfidfIndex:
    catalog = load_catalog(path_str)
    return build_index(
        catalog["exemplars"],
        catalog_version=catalog["catalog_version"],
    )


def get_index(path: str | Path | None = None) -> tuple[TfidfIndex, dict[str, Any]]:
    catalog = load_catalog(path)
    catalog_path = Path(catalog["path"])
    index = _cached_index(str(catalog_path), catalog_path.stat().st_mtime_ns)
    return index, catalog


def route_unstructured(
    text: str,
    *,
    claim_id: str | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    margin: float = DEFAULT_MARGIN,
    exemplars_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return cosine triage. Does not call an LLM.

    ``needs_llm`` is true when the top score is below ``threshold`` or the
    top-two labels are too close (margin). Orchestrator/Routing Agent then
    runs a bounded LLM classify. If ``claim_id`` is set, structured claim
    intake still wins.
    """
    query = (text or "").strip()
    index, catalog = get_index(exemplars_path)
    hit = cosine_search(query, index) if query else {
        "score": 0.0,
        "margin": 0.0,
        "label": None,
        "matched_exemplar_id": None,
        "second_label": None,
        "second_score": 0.0,
        "scores_by_label": {},
    }
    score = float(hit["score"] or 0.0)
    hit_margin = float(hit["margin"] or 0.0)
    label = hit["label"]
    close_call = (
        hit["second_label"] is not None
        and hit["second_label"] != label
        and hit_margin < margin
    )
    below = (not query) or score < threshold or close_call
    method = "below_threshold" if below else "cosine"
    dispatch_map = catalog.get("dispatch") or DISPATCH
    dispatch = dispatch_map.get(label or "", {})
    cid = (claim_id or "").strip() or None
    return {
        "content_id": CONTENT_ID,
        "method": method,
        "needs_llm": below,
        "label": None if below else label,
        "suggested_label": label,
        "score": round(score, 6),
        "margin": round(hit_margin, 6),
        "threshold": threshold,
        "min_margin": margin,
        "matched_exemplar_id": hit["matched_exemplar_id"],
        "second_label": hit["second_label"],
        "second_score": round(float(hit["second_score"] or 0.0), 6),
        "scores_by_label": {
            k: round(float(v), 6) for k, v in (hit["scores_by_label"] or {}).items()
        },
        "coworker": None if below else dispatch.get("coworker"),
        "agent_role": None if below else dispatch.get("agent_role"),
        "next_step": None if below else dispatch.get("next_step"),
        "lane": None if below else dispatch.get("lane"),
        "claim_id": cid,
        "structured_intake_supersedes": bool(cid),
        "authority": "advisory" if cid else "nl_triage",
        "catalog_version": index.catalog_version,
        "catalog_path": catalog["path"],
        "notes": (
            "If claim_id is present, structured claim intake (spine → signals → "
            "build → validate → route) is authoritative; cosine is NL triage only."
            if cid
            else "No claim_id: cosine/LLM triage may dispatch a specialist. "
            "Do not invent SQL or skip structured claim intake when a claim_id "
            "is later supplied."
        ),
    }
