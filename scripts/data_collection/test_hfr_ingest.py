"""Tests for the bounded HFR source import."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("ingest_hfr.py")
INTERIM = ROOT / "data" / "interim" / "hfr"


class HfrIngestTests(unittest.TestCase):
    def test_excel_serial_date_hand_computed(self) -> None:
        namespace: dict[str, object] = {}
        namespace["__file__"] = str(SCRIPT)
        exec(SCRIPT.read_text(encoding="utf-8"), namespace)
        serial_date = namespace["serial_date"]
        self.assertEqual(serial_date("46234"), (date(1899, 12, 30) + timedelta(days=46234)).isoformat())
        self.assertIsNone(serial_date(""))
        with self.assertRaises(ValueError):
            serial_date("46234", date1904=True)

    def test_ingest_reproduces_bounded_extract_and_preserves_blank(self) -> None:
        subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
        first_bytes = (INTERIM / "hfr_index_constituents.jsonl").read_bytes()
        subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
        self.assertEqual(first_bytes, (INTERIM / "hfr_index_constituents.jsonl").read_bytes())
        manifest = json.loads((INTERIM / "hfr_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["extract"]["row_count"], 13014)
        self.assertEqual(manifest["extract"]["index_count"], 180)
        first = (INTERIM / "hfr_index_constituents.jsonl").read_text(encoding="utf-8").splitlines()[2]
        self.assertIn('"Approx_Weight":null', first)
        self.assertIn('"_excel_row":4', first)

    def test_hfri_event_driven_series_source_pins(self) -> None:
        records = [json.loads(line) for line in (INTERIM / "hfri_event_driven_2703_monthly.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 440)
        self.assertEqual(records[0]["Fund"], "HFRI Event-Driven (Total) Index")
        self.assertEqual(records[0]["Date"], "1990-01-31")
        self.assertEqual(records[0]["ROR"], "-5.69")
        self.assertEqual(records[-1]["Date"], "2026-08-31")
        dates = [date.fromisoformat(record["Date"]) for record in records]
        self.assertEqual(len(set(dates)), 440)
        self.assertEqual(sum((b.year - a.year) * 12 + b.month - a.month == 1 for a, b in zip(dates, dates[1:], strict=False)), 439)
        metadata = json.loads((INTERIM / "hfr_manifest.json").read_text(encoding="utf-8"))["hfri_event_driven_2703"]["fund_metadata_evidence"]
        self.assertEqual((metadata["Fund"], metadata["currency"], metadata["fee_label"]), ("HFRI Event-Driven (Total) Index", "USD", "Net of All Fees"))


if __name__ == "__main__":
    unittest.main()
