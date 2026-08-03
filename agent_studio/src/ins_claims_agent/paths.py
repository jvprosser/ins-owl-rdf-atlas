"""Resolve repo-relative paths for ontology, probes, and playbook."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def _find_repo_root() -> Path:
    """Locate ontology/ + playbook/ markers.

    Order:
    1. ``INS_CLAIMS_REPO_ROOT`` env (Agent Studio / explicit deploy root)
    2. Walk upward from this package
    """
    env = os.environ.get("INS_CLAIMS_REPO_ROOT")
    if env:
        candidate = Path(env).expanduser().resolve()
        if (candidate / "ontology" / "claims_mvt.ttl").is_file() and (
            candidate / "playbook" / "playbook.yaml"
        ).is_file():
            return candidate
        raise FileNotFoundError(
            f"INS_CLAIMS_REPO_ROOT={candidate} missing ontology/claims_mvt.ttl "
            "and/or playbook/playbook.yaml"
        )

    for candidate in [PACKAGE_DIR, *PACKAGE_DIR.parents]:
        if (candidate / "ontology" / "claims_mvt.ttl").is_file() and (
            candidate / "playbook" / "playbook.yaml"
        ).is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate repo root containing ontology/claims_mvt.ttl and "
        "playbook/playbook.yaml (set INS_CLAIMS_REPO_ROOT if needed)"
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
