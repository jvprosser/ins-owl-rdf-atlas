"""Evaluate playbook YAML match clauses against a case JSON document."""

from __future__ import annotations

from typing import Any


def get_path(doc: dict[str, Any], path: str | None) -> Any:
    if not path:
        return doc
    cur: Any = doc
    for part in str(path).split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    # Studio build_claim_graph pin 8f60419 nested MCP signals but omitted
    # top-level R6/R5.2 fields. Probes read the document root.
    if cur is None and isinstance(doc, dict) and "." not in str(path):
        nested = doc.get("signals")
        if isinstance(nested, dict):
            return nested.get(str(path))
    return cur


def eval_match(match: dict[str, Any] | None, case: dict[str, Any]) -> bool:
    if not match:
        return False
    if "all" in match:
        return all(eval_match(item, case) for item in match["all"])
    if "any" in match:
        return any(eval_match(item, case) for item in match["any"])
    if "not" in match:
        inner = match["not"]
        if isinstance(inner, dict):
            return not eval_match(inner, case)
        return not bool(inner)
    return eval_pred(match, case)


def eval_pred(pred: dict[str, Any], case: dict[str, Any]) -> bool:
    value = get_path(case, pred.get("path"))
    if "equals" in pred:
        return _equals(value, pred["equals"])
    if "exists" in pred:
        exists = value not in (None, "", [], {})
        return exists is bool(pred["exists"])
    if "empty" in pred:
        empty = value in (None, "", [], {})
        return empty is bool(pred["empty"])
    if "in" in pred:
        return value in list(pred["in"])
    if "contains" in pred:
        needle = pred["contains"]
        if isinstance(value, list):
            if needle in value:
                return True
            if isinstance(needle, dict):
                return any(
                    isinstance(item, dict)
                    and all(item.get(k) == v for k, v in needle.items())
                    for item in value
                )
            return False
        if isinstance(value, str):
            return str(needle) in value
        return False
    return bool(value)


def _equals(left: Any, right: Any) -> bool:
    if left is None and right is None:
        return True
    if isinstance(right, bool) or isinstance(left, bool):
        return bool(left) is bool(right) and left is not None
    return left == right
