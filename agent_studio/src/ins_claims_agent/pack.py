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
    schema: str = "ontology/claims.json"
    playbook: str = "playbook/playbook.yaml"
    exemplars: str = "exemplars.yaml"
    graph: dict[str, Any] = field(default_factory=dict)
    catalog: dict[str, Any] = field(default_factory=dict)
    cosine_labels: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    def path(self, rel: str) -> Path:
        return (self.root / rel).resolve()

    @property
    def schema_path(self) -> Path:
        return self.path(self.schema)

    @property
    def ontology_path(self) -> Path:
        return self.schema_path

    @property
    def playbook_path(self) -> Path:
        return self.path(self.playbook)

    @property
    def exemplars_path(self) -> Path:
        return self.path(self.exemplars)


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
        schema=str(
            raw.get("schema")
            or raw.get("ontology")
            or "ontology/claims.json"
        ),
        playbook=str(raw.get("playbook") or "playbook/playbook.yaml"),
        exemplars=str(raw.get("exemplars") or "exemplars.yaml"),
        graph=dict(raw.get("graph") or {}),
        catalog=dict(raw.get("catalog") or {}),
        cosine_labels=tuple(raw.get("cosine_labels") or ()),
        raw=raw,
    )


def is_pack_root(candidate: Path) -> bool:
    return (candidate / "pack.yaml").is_file()


def is_legacy_claims_root(candidate: Path) -> bool:
    playbook = (candidate / "playbook" / "playbook.yaml").is_file()
    schema = (candidate / "ontology" / "claims.json").is_file()
    return playbook and schema
