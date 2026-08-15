"""Pack-driven RDF graph build (literals/booleans on a case IRI)."""

from __future__ import annotations

from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from ins_claims_agent.pack import Pack
from ins_claims_agent.studio_io import normalize_signals_payload, normalize_spine_payload

EX = Namespace("https://example.org/ins/")


def build_case_graph(
    case_id: int | str,
    *,
    pack: Pack,
    spine: dict[str, Any] | str | None = None,
    signals: dict[str, Any] | str | None = None,
) -> Graph:
    """Load pack TBox and assert mapped spine/signal fields on the case IRI."""
    spine = normalize_spine_payload(spine or {})
    signals = normalize_signals_payload(signals or {})
    merged: dict[str, Any] = {}
    if isinstance(spine, dict):
        inner = spine.get("spine") if isinstance(spine.get("spine"), dict) else spine
        merged.update(inner)
    if isinstance(signals, dict):
        inner_s = signals.get("signals") if isinstance(signals.get("signals"), dict) else signals
        merged.update(inner_s)

    g = Graph()
    g.bind("ex", EX)
    g.parse(str(pack.ontology_path), format="turtle")

    case = URIRef(pack.case_iri(case_id))
    case_class = str(pack.graph.get("case_class") or "Case")
    g.add((case, RDF.type, EX[case_class]))

    for field, pred in (pack.graph.get("literals") or {}).items():
        _add_literal(g, case, EX[str(pred)], merged.get(field), XSD.string)
    for field, pred in (pack.graph.get("booleans") or {}).items():
        _add_bool(g, case, EX[str(pred)], merged.get(field))
    return g


def _add_literal(g: Graph, s: URIRef, p: URIRef, value: Any, datatype: URIRef) -> None:
    if value is None:
        return
    if datatype == XSD.string:
        g.add((s, p, Literal(str(value))))
        return
    g.add((s, p, Literal(value, datatype=datatype)))


def _add_bool(g: Graph, s: URIRef, p: URIRef, value: Any) -> None:
    if value is None:
        return
    g.add((s, p, Literal(bool(value), datatype=XSD.boolean)))
