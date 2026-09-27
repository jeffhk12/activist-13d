"""Tier: 1. Hand-pinned history and reproducibility contracts for Phase 2 staging.
Inputs: synthetic disclosures. Output: unittest assertions; no sources/network.
Identity: only earlier acceptance timestamps can contribute historical CIK counts.
Run: project Python scripts/phase2_overnight/test_staging.py
"""

import unittest

from run import histories


def row(a, t, reporters, issuers):
    return dict(accession=a, accepted=t, reporter_ciks=reporters, issuers=issuers)


class HistoryTests(unittest.TestCase):
    def test_other_company_does_not_establish_current_company(self):
        data = [row("a", "2020-01-01", ["R"], ["B"]), row("b", "2020-01-02", ["R"], ["A"])]
        h = histories(data)["b"]
        self.assertEqual(h["reporter_history"][0]["prior_other_issuer_count"], 1)
        self.assertEqual(h["issuer_history"][0]["prior_distinct_reporter_ciks"], 0)

    def test_simultaneous_and_future_excluded(self):
        data = [row("a", "2020-01-01", ["R"], ["A"]), row("b", "2020-01-01", ["R"], ["A"])]
        self.assertEqual(histories(data)["b"]["reporter_history"][0]["prior_submission_count"], 0)
        self.assertEqual(
            histories(data),
            {
                k: v
                for k, v in histories(data + [row("c", "2030-01-01", ["R"], ["B"])]).items()
                if k != "c"
            },
        )

    def test_duplicate_reporters_are_not_extra_investors(self):
        data = [row("a", "2020-01-01", ["R", "R"], ["A"]), row("b", "2020-01-02", ["S"], ["A"])]
        self.assertEqual(
            histories(data)["b"]["issuer_history"][0]["prior_reporter_ciks_outside_current_group"],
            1,
        )

    def test_missing_time_and_id_remain_unavailable(self):
        self.assertEqual(histories([row("a", None, ["R"], ["A"])]), {})
        self.assertEqual(
            histories([row("a", "2020-01-01", [], ["A"])])["a"]["reporter_history"], []
        )

    def test_reordering_reproduces_results(self):
        data = [row("a", "2020-01-01", ["R"], ["A"]), row("b", "2020-01-02", ["R"], ["B"])]
        self.assertEqual(histories(data), histories(list(reversed(data))))


if __name__ == "__main__":
    unittest.main()
