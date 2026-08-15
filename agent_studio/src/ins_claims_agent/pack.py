"""Load a domain pack (pack.yaml) from WORKFLOW_DATA / PACK_ROOT."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Pack:
    id: str
    root: Path
    case_id_param: str = "claim_id"
    iri_template: str = "https://example.org/ins/id/Claim/{case_id}"
    ontology: str = "ontology/claims_mvt.ttl"
    playbook: str = "playbook/playbook.yaml"
    probes: str = "probes"
    exemplars: str = "exemplars.yaml"
    graph: dict[str, Any] = field(default_factory=dict)
    catalog: dict[str, Any] = field(default_factory=dict)
    cosine_labels: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    def path(self, rel: str) -> Path:
        return (self.root / rel).resolve()

    @property
    def ontology_path(self) -> Path:
        return self.path(self.ontology)

    @property
    def playbook_path(self) -> Path:
        return self.path(self.playbook)

    @property
    def probes_dir(self) -> Path:
        return self.path(self.probes)

    @property
    def exemplars_path(self) -> Path:
        return self.path(self.exemplars)

    def case_iri(self, case_id: int | str) -> str:
        return self.iri_template.format(case_id=case_id, claim_id=case_id)


def load_pack(root: str | Path) -> Pack:
    root_path = Path(root).expanduser().resolve()
    pack_file = root_path / "pack.yaml"
    if not pack_file.is_file():
        raise FileNotFoundError(f"pack.yaml not found under {root_path}")
    raw = yaml.safe_load(pack_file.read_text(encoding="utf-8")) or {}
    return Pack(
        id=str(raw.get("id") or root_path.name),
        root=root_path,
        case_id_param=str(raw.get("case_id_param") or "claim_id"),
        iri_template=str(
            raw.get("iri_template")
            or "https://example.org/ins/id/Claim/{case_id}"
        ),
        ontology=str(raw.get("ontology") or "ontology/claims_mvt.ttl"),
        playbook=str(raw.get("playbook") or "playbook/playbook.yaml"),
        probes=str(raw.get("probes") or "probes"),
        exemplars=str(raw.get("exemplars") or "exemplars.yaml"),
        graph=dict(raw.get("graph") or {}),
        catalog=dict(raw.get("catalog") or {}),
        cosine_labels=tuple(raw.get("cosine_labels") or ()),
        raw=raw,
    )


def is_pack_root(candidate: Path) -> bool:
    return (candidate / "pack.yaml").is_file()


def is_legacy_claims_root(candidate: Path) -> bool:
    return (candidate / "ontology" / "claims_mvt.ttl").is_file() and (
        candidate / "playbook" / "playbook.yaml"
    ).is_file()
