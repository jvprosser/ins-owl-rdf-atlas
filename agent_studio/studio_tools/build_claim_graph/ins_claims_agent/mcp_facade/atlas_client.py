"""Facade for data-contract-mcp-server (+ claims fork BM bind tools when available)."""

from __future__ import annotations

from typing import Any

from .base import McpToolCaller

SERVER = "data-contract-mcp-server"


class AtlasFacade(McpToolCaller):
    """Atlas / data-contract MCP access. Primary Atlas interface (do not dual-register ecole5)."""

    def search_entities(self, query: str = "*", **kwargs: Any) -> Any:
        return self.call(SERVER, "search_entities", query=query, **kwargs)

    def dsl_search(self, query: str, **kwargs: Any) -> Any:
        return self.call(SERVER, "dsl_search", query=query, **kwargs)

    def get_entity(self, guid: str, ignore_relationships: bool = False) -> Any:
        return self.call(
            SERVER, "get_entity", guid=guid, ignore_relationships=ignore_relationships
        )

    def get_entity_by_attribute(self, type_name: str, attr_name: str, attr_value: str) -> Any:
        return self.call(
            SERVER,
            "get_entity_by_attribute",
            type_name=type_name,
            attr_name=attr_name,
            attr_value=attr_value,
        )

    def add_classification_to_entity(
        self, guid: str, classification_name: str, attributes: dict[str, Any] | None = None
    ) -> Any:
        kwargs: dict[str, Any] = {
            "guid": guid,
            "classification_name": classification_name,
        }
        if attributes is not None:
            kwargs["attributes"] = attributes
        return self.call(SERVER, "add_classification_to_entity", **kwargs)

    def add_labels_to_entity(self, guid: str, labels: str) -> Any:
        return self.call(SERVER, "add_labels_to_entity", guid=guid, labels=labels)

    def ensure_data_contract_typedef(self) -> Any:
        return self.call(SERVER, "ensure_data_contract_typedef")

    def create_data_contract(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "create_data_contract", **kwargs)

    def bind_contract_to_table(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "bind_contract_to_table", **kwargs)

    def search_data_contracts(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "search_data_contracts", **kwargs)

    # --- claims fork P0 ---

    def ensure_business_metadata_typedef(self, bm_name: str, attributes: list[dict[str, Any]]) -> Any:
        return self.call(
            SERVER,
            "ensure_business_metadata_typedef",
            bm_name=bm_name,
            attributes=attributes,
        )

    def set_entity_business_metadata(
        self, guid: str, bm_name: str, attributes: dict[str, Any]
    ) -> Any:
        return self.call(
            SERVER,
            "set_entity_business_metadata",
            guid=guid,
            bm_name=bm_name,
            attributes=attributes,
        )

    def get_entity_business_metadata(self, guid: str, bm_name: str | None = None) -> Any:
        kwargs: dict[str, Any] = {"guid": guid}
        if bm_name is not None:
            kwargs["bm_name"] = bm_name
        return self.call(SERVER, "get_entity_business_metadata", **kwargs)

    def bind_ontology_iri_to_entity(
        self,
        guid: str,
        ontology_iri: str,
        mapping_type: str,
        version_iri: str | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "guid": guid,
            "ontology_iri": ontology_iri,
            "mapping_type": mapping_type,
        }
        if version_iri is not None:
            kwargs["version_iri"] = version_iri
        return self.call(SERVER, "bind_ontology_iri_to_entity", **kwargs)
