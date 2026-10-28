"""BPMN diagram coordinate updates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bpmn_layout import apply_positions, write_positions

SAMPLE = """
<bpmndi:BPMNShape bpmnElement="CollectIncidentReportNumber" id="Shape_Collect">
  <dc:Bounds x="420" y="156" width="180" height="70"/>
</bpmndi:BPMNShape>
<bpmndi:BPMNShape bpmnElement="End" id="Shape_End">
  <dc:Bounds x="40" y="1008" width="50" height="50"/>
</bpmndi:BPMNShape>
"""


class BpmnLayoutTests(unittest.TestCase):
    def test_apply_positions_updates_matching_shapes_only(self) -> None:
        xml, count = apply_positions(SAMPLE, {"CollectIncidentReportNumber": (500.16, 180)})
        self.assertEqual(count, 1)
        self.assertIn('bpmnElement="CollectIncidentReportNumber"', xml)
        self.assertIn('x="500.2" y="180" width="180" height="70"', xml)
        self.assertIn('x="40" y="1008" width="50" height="50"', xml)

    def test_write_positions_rejects_unknown_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diagram.bpmn"
            path.write_text(SAMPLE, encoding="utf-8")
            with self.assertRaises(ValueError):
                write_positions(path, {"Missing": (1, 2)})
            self.assertEqual(path.read_text(encoding="utf-8"), SAMPLE)
