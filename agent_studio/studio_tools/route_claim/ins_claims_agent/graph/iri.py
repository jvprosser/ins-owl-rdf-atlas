"""IRI helpers for claim-run graphs (D6: surrogate ids in IRI path)."""

from __future__ import annotations

IRI_BASE = "https://example.org/ins/"
ID_BASE = f"{IRI_BASE}id/"


def claim_iri(claim_id: int | str) -> str:
    return f"{ID_BASE}Claim/{claim_id}"


def entity_iri(kind: str, entity_id: int | str) -> str:
    return f"{ID_BASE}{kind}/{entity_id}"


def term_iri(local: str) -> str:
    return f"{IRI_BASE}{local}"
