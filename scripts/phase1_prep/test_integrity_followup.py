"""Refusal and replay contracts for the offline integrity follow-up.

Inputs: synthetic source, sidecar, date and index records. Outputs: assertions.
Identity: a three-byte source must report three bytes; all dates must agree.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest discover -s scripts/phase1_prep
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import integrity_followup
from integrity_followup import _safe, filed_as_of, index_rows, verify_packet


class IntegrityFollowupTests(unittest.TestCase):
    def test_raw_filed_date(self):
        self.assertEqual(filed_as_of(b"FILED AS OF DATE:\t\t20240102"), "2024-01-02")
        self.assertIsNone(filed_as_of(b"no date"))
        self.assertIsNone(filed_as_of(b"FILED AS OF DATE:\t\t20241399"))

    def test_url_sidecar_and_packet_replay_refuse_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "x.html"
            path.write_text("blank packet")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(verify_packet(path, expected)["status"], "verified")
            self.assertEqual(verify_packet(path, "0" * 64)["status"], "integrity_failure")
            raw_root = Path(folder) / "raw"
            raw_root.mkdir()
            source = raw_root / "x.txt"
            source.write_bytes(b"abc")
            sidecar = Path(str(source) + ".meta.json")
            sidecar.write_text(json.dumps({"url": "https://good/x", "sha256": hashlib.sha256(b"abc").hexdigest(), "bytes": 3}))
            old_root = integrity_followup.RAW
            integrity_followup.RAW = raw_root
            try:
                with self.assertRaises(ValueError):
                    integrity_followup.verify_submission(source, {"source_url": "https://bad/x", "source_sha256": hashlib.sha256(b"abc").hexdigest()})
                record = {"source_url": "https://good/x", "source_sha256": hashlib.sha256(b"abc").hexdigest()}
                self.assertEqual(integrity_followup.verify_submission(source, record), b"abc")
                meta = json.loads(sidecar.read_text())
                meta["bytes"] = 4
                sidecar.write_text(json.dumps(meta))
                with self.assertRaises(ValueError):
                    integrity_followup.verify_submission(source, record)
            finally:
                integrity_followup.RAW = old_root

    def test_path_containment_refuses_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "raw"
            root.mkdir()
            with self.assertRaises(ValueError):
                _safe(root, "../outside.txt")

    def test_index_date_row_and_missing_accession_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "form.idx"
            path.write_text("Description: x\nSC 13D  Issuer  123  2024-01-02  edgar/data/123/0000000000-24-000001.txt\n")
            rows = index_rows([path], {"0000000000-24-000001"})
            self.assertEqual(rows["0000000000-24-000001"]["filing_date"], "2024-01-02")
            self.assertNotIn("missing", rows)
            with path.open("a") as handle:
                handle.write("SC 13D  Issuer  123  2024-01-03  edgar/data/123/0000000000-24-000001.txt\n")
            with self.assertRaises(ValueError):
                index_rows([path], {"0000000000-24-000001"})

    def test_date_disagreement_refuses(self):
        integrity_followup.verify_dates("2024-01-02", "2024-01-02", "2024-01-02")
        with self.assertRaises(ValueError):
            integrity_followup.verify_dates("2024-01-02", "2024-01-03")
        with self.assertRaises(ValueError):
            integrity_followup.verify_dates(None, None)


if __name__ == "__main__":
    unittest.main()
