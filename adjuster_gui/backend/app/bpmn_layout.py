"""Update BPMN diagram coordinates without rewriting the rest of the file."""

from __future__ import annotations

import re
from pathlib import Path

_SHAPE = re.compile(
    r'(<bpmndi:BPMNShape\b[^>]*\bbpmnElement=")([^"]+)("[^>]*>\s*<dc:Bounds\b)([^>]*?)(/>)',
    re.DOTALL,
)


def format_coord(value: float) -> str:
    number = round(float(value), 1)
    if number == int(number):
        return str(int(number))
    return f"{number:.1f}"


def apply_positions(xml: str, positions: dict[str, tuple[float, float]]) -> tuple[str, int]:
    """Set Bounds x/y for shapes whose bpmnElement id is in positions."""
    updated = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal updated
        element_id = match.group(2)
        pos = positions.get(element_id)
        if pos is None:
            return match.group(0)
        bounds = match.group(4)
        if 'x="' not in bounds or 'y="' not in bounds:
            return match.group(0)
        bounds = re.sub(r'\bx="[^"]*"', f'x="{format_coord(pos[0])}"', bounds, count=1)
        bounds = re.sub(r'\by="[^"]*"', f'y="{format_coord(pos[1])}"', bounds, count=1)
        updated += 1
        return f"{match.group(1)}{element_id}{match.group(3)}{bounds}{match.group(5)}"

    return _SHAPE.sub(repl, xml), updated


def write_positions(path: Path, positions: dict[str, tuple[float, float]]) -> int:
    xml, count = apply_positions(path.read_text(encoding="utf-8"), positions)
    if count == 0:
        raise ValueError("No BPMN shapes matched the graph.")
    path.write_text(xml, encoding="utf-8")
    return count
