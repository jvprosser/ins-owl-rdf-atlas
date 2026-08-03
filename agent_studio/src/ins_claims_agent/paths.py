"""Resolve repo-relative paths for ontology, probes, and playbook."""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def _find_repo_root() -> Path:
    """Walk upward until ontology/ + playbook/ markers are found."""
    for candidate in [PACKAGE_DIR, *PACKAGE_DIR.parents]:
        if (candidate / "ontology" / "claims_mvt.ttl").is_file() and (
            candidate / "playbook" / "playbook.yaml"
        ).is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate repo root containing ontology/claims_mvt.ttl and playbook/playbook.yaml"
    )


REPO_ROOT = _find_repo_root()


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def default_playbook_path() -> Path:
    return repo_path("playbook", "playbook.yaml")


def default_ontology_path() -> Path:
    return repo_path("ontology", "claims_mvt.ttl")


def default_probes_dir() -> Path:
    return repo_path("probes")
