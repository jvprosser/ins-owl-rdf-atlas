"""Resolve repo-relative paths for ontology, probes, and playbook."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def _has_assets(candidate: Path) -> bool:
    return (candidate / "ontology" / "claims_mvt.ttl").is_file() and (
        candidate / "playbook" / "playbook.yaml"
    ).is_file()


def _find_repo_root() -> Path:
    """Locate ontology/ + playbook/ markers.

    Order:
    1. ``INS_CLAIMS_REPO_ROOT`` env (explicit / tool override)
    2. ``WORKFLOW_DATA_DIRECTORY`` (Agent Studio RO config mount)
    3. Walk upward from this package
    """
    env = os.environ.get("INS_CLAIMS_REPO_ROOT")
    if env:
        candidate = Path(env).expanduser().resolve()
        if _has_assets(candidate):
            return candidate
        raise FileNotFoundError(
            f"INS_CLAIMS_REPO_ROOT={candidate} missing ontology/claims_mvt.ttl "
            "and/or playbook/playbook.yaml"
        )

    wf = os.environ.get("WORKFLOW_DATA_DIRECTORY")
    if wf:
        candidate = Path(wf).expanduser().resolve()
        if _has_assets(candidate):
            return candidate

    for candidate in [PACKAGE_DIR, *PACKAGE_DIR.parents]:
        if _has_assets(candidate):
            return candidate
    raise FileNotFoundError(
        "Could not locate ontology/claims_mvt.ttl and playbook/playbook.yaml "
        "(set WORKFLOW_DATA_DIRECTORY or INS_CLAIMS_REPO_ROOT)"
    )


def repo_root() -> Path:
    return _find_repo_root()


# Eager default for local package use; Agent Studio tools should set
# INS_CLAIMS_REPO_ROOT before importing graph modules when assets are bundled.
try:
    REPO_ROOT = _find_repo_root()
except FileNotFoundError:
    REPO_ROOT = PACKAGE_DIR.parents[2]


def repo_path(*parts: str) -> Path:
    return repo_root().joinpath(*parts)


def default_playbook_path() -> Path:
    return repo_path("playbook", "playbook.yaml")


def default_ontology_path() -> Path:
    return repo_path("ontology", "claims_mvt.ttl")


def default_probes_dir() -> Path:
    return repo_path("probes")
