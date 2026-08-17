"""Resolve repo-relative paths for schema JSON and playbook YAML."""

from __future__ import annotations

import os
from pathlib import Path

from ins_claims_agent.pack import is_legacy_claims_root, is_pack_root, load_pack

PACKAGE_DIR = Path(__file__).resolve().parent


def _has_assets(candidate: Path) -> bool:
    return is_pack_root(candidate) or is_legacy_claims_root(candidate)


def _find_repo_root() -> Path:
    """Locate a pack.yaml or ontology/ + playbook/ tree.

    Order:
    1. ``PACK_ROOT`` / ``INS_CLAIMS_REPO_ROOT``
    2. ``WORKFLOW_DATA_DIRECTORY``
    3. Walk upward from this package
    """
    for key in ("PACK_ROOT", "INS_CLAIMS_REPO_ROOT"):
        env = os.environ.get(key)
        if env:
            candidate = Path(env).expanduser().resolve()
            if _has_assets(candidate):
                return candidate
            raise FileNotFoundError(
                f"{key}={candidate} missing pack.yaml or ontology/ + playbook/"
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
        "Could not locate pack.yaml or ontology/claims.json + playbook/ "
        "(set WORKFLOW_DATA_DIRECTORY, PACK_ROOT, or INS_CLAIMS_REPO_ROOT)"
    )


def repo_root() -> Path:
    return _find_repo_root()


try:
    REPO_ROOT = _find_repo_root()
except FileNotFoundError:
    REPO_ROOT = PACKAGE_DIR.parents[2]


def repo_path(*parts: str) -> Path:
    return repo_root().joinpath(*parts)


def current_pack():
    root = repo_root()
    if is_pack_root(root):
        return load_pack(root)
    return None


def default_playbook_path() -> Path:
    pack = current_pack()
    if pack is not None:
        return pack.playbook_path
    return repo_path("playbook", "playbook.yaml")


def default_ontology_path() -> Path:
    pack = current_pack()
    if pack is not None:
        return pack.schema_path
    return repo_path("ontology", "claims.json")
