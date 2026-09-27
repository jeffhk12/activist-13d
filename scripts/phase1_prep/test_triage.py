"""Contracts for the offline Phase 1 exception triage artifact.

Inputs: latest exploratory artifact and completed cached source records.
Outputs: source hash/span and explicit uncertainty assertions.
Identity: every candidate span equals document text[start:end].
Tier: 1
Run: python scripts/phase1_prep/test_triage.py
"""

import glob
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TriageArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = sorted(glob.glob(str(ROOT / "research/runs/phase1-prep/triage-*/triage.json")))
        if not paths:
            raise AssertionError("run triage.py first")
        cls.data = json.loads(Path(paths[-1]).read_text())
        cls.sources = {r["accession"]: r for r in (
            json.loads(line) for line in (ROOT / "research/runs/phase1-prep/20260914T003050627334Z/reparsed-records.jsonl").read_text().splitlines())}

    def test_metadata_declares_offline_model_and_inputs(self):
        meta = self.data["metadata"]
        self.assertEqual(meta["model"], "gpt-5.6-luna")
        self.assertTrue(meta["offline"])
        self.assertTrue(meta["input_hashes"]["records_sha256"])

    def test_expected_flag_rows_and_overlap_count(self):
        self.assertEqual(len(self.data["records"]), 36)
        self.assertEqual(sum(r["flag"] == "binary_document_requires_review" for r in self.data["records"]), 7)

    def test_every_source_hash_is_verified(self):
        for row in self.data["records"]:
            actual = hashlib.sha256((ROOT / row["source_path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, row["source_sha256_recorded"])
            self.assertEqual(actual, row["source_sha256_observed"])

    def test_candidates_have_exact_spans_and_cannot_determine_is_explicit(self):
        for row in self.data["records"]:
            if row["status"] == "candidate_for_human_review":
                self.assertIsNotNone(row["source_span"])
                self.assertTrue(row["source_span"]["text"])
                span = row["source_span"]
                doc = self.sources[row["accession"]]["documents"][span["document_index"] - 1]
                self.assertEqual(doc["text"][span["start"]:span["end"]], span["text"])
                self.assertEqual(row["candidate"], span["text"])
                if "context_start" in span:
                    self.assertEqual(doc["text"][span["context_start"]:span["context_end"]], span["context_text"])
            else:
                self.assertEqual(row["status"], "cannot_determine")


if __name__ == "__main__":
    unittest.main()
