"""Tier: 1. Hand-computed coverage and independent-history tests.
Inputs: synthetic records. Outputs: unittest results. Identity: strict earlier time.
Run: project Python scripts/phase2_readiness/test_readiness.py
"""

import unittest

from run import independent_history, index_history, ownership_coverage


def row(a, t, r, i):
    return dict(accession=a, accepted=t, reporter_ciks=r, issuers=i)


class Tests(unittest.TestCase):
    def test_strict_time_and_other_issuer(self):
        rows = [
            row("a", "2020", ["R"], ["B"]),
            row("b", "2021", ["R"], ["A"]),
            row("c", "2021", ["R"], ["A"]),
            row("d", "2022", ["R"], ["C"]),
        ]
        h = independent_history(rows[1], index_history(rows))
        self.assertEqual(h["reporter_history"][0]["prior_submission_count"], 1)
        self.assertEqual(h["reporter_history"][0]["prior_other_issuer_count"], 1)
        self.assertEqual(h["issuer_history"][0]["prior_distinct_reporter_ciks"], 0)

    def test_unique_reporters_and_reproducibility(self):
        rows = [row("a", "2020", ["R", "R"], ["A"]), row("b", "2021", ["S"], ["A"])]
        h = independent_history(rows[1], index_history(rows))
        self.assertEqual(h["issuer_history"][0]["prior_reporter_ciks_outside_current_group"], 1)
        self.assertEqual(h, independent_history(rows[1], index_history(list(reversed(rows)))))

    def test_zero_rows_not_complete(self):
        self.assertFalse(ownership_coverage([])["percent_of_class"]["all_present"])

    def test_missing_percentage_not_zero(self):
        r = ownership_coverage(
            [
                {"percent_of_class": {"status": "present"}},
                {"percent_of_class": {"status": "ambiguous"}},
            ]
        )
        self.assertEqual(r["percent_of_class"]["present"], 1)
        self.assertEqual(r["percent_of_class"]["rows"], 2)
        self.assertFalse(r["percent_of_class"]["all_present"])


if __name__ == "__main__":
    unittest.main()
