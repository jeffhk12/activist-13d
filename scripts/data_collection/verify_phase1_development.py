"""Tier: 1. Independently reconcile development ledger, boundaries and provenance.

Inputs: frozen development-v4 outputs. Output: separate verification receipt.
Identities: all = broad + other; mean excess = sum(stock - benchmark)/n;
issuer intervals do not overlap; protected issuers and 2024+ outcomes absent.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_phase1_development.py
"""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'research/runs/phase1-baseline/20260924-development-v4'
OUT = ROOT / 'research/runs/phase1-baseline/20260924-development-verification-v4'


class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == 'href':
                url = urlsplit(value)
                if not url.scheme and url.path:
                    assert (RUN / unquote(url.path)).resolve().exists(), value


def main():
    results = json.loads((RUN / 'outcomes.json').read_text())
    summaries = json.loads((RUN / 'summary.json').read_text())
    selection = json.loads((RUN / 'selection.json').read_text())
    protection = json.loads((RUN / 'human-review-protection.json').read_text())
    protected = set(protection['issuers'])
    panel = json.loads((RUN / 'daily-panel.json').read_text())['panel']
    assert set(results) == {'63', '126', '252'}
    for horizon, rows in results.items():
        assert len(rows) == len(selection['plans'][horizon])
        assert all(r['issuer'] not in protected and r['exit'] <= '2023-12-29'
                   and '2018-03-19' <= r['entry'] <= '2022-12-30' for r in rows)
        valid = [r for r in rows if r['excess'] is not None]
        assert len(valid) == summaries[horizon]['all']['calculated']
        assert abs(sum(r['stock_return'] - r['benchmark_return'] for r in valid)
                   / len(valid) - summaries[horizon]['all']['mean_excess']) < 1e-12
        assert all(not r['focused'] or r['broad'] for r in rows)
        for event in valid:
            securities = [84398]
            if event['stock_status'] == 'calculated_full_window':
                securities.append(event['permno'])
            for security in securities:
                last = panel[str(security)][event['exit']]
                assert float(last['dlyclose']) > 0 and float(last['dlyvol']) > 0
                assert last['conditionaltype'] == 'RW' and last['tradingstatusflg'] == 'A'
        assert (summaries[horizon]['all']['calculated'] == summaries[horizon]['broad']['calculated']
                + summaries[horizon]['other']['calculated'])
        for issuer in {r['issuer'] for r in rows}:
            events = sorted([r for r in rows if r['issuer'] == issuer], key=lambda r: r['entry'])
            assert all(a['exit'] < b['entry'] for a, b in zip(events, events[1:], strict=False))
    provenance = json.loads((RUN / 'provenance.json').read_text())
    for name, expected in provenance['files'].items():
        assert hashlib.sha256((RUN / name).read_bytes()).hexdigest() == expected, name
    Links().feed((RUN / 'index.html').read_text())
    # Repair changes data availability, never outcome-driven entry choices.
    previous = RUN.parent / '20260924-development-v2'
    assert (RUN / 'selection.json').read_bytes() == (previous / 'selection.json').read_bytes()
    assert (RUN / 'protocol.md').read_bytes() == (previous / 'protocol.md').read_bytes()
    receipt = dict(ledger_reconciles=True, protected_issuers_excluded=True,
        no_2024_or_later_outcomes=True, no_overlapping_issuer_positions=True,
        mean_excess_independently_recomputed=True, output_hashes_verified=True,
        report_links_verified=True, identical_selection_before_and_after_gap_repair=True,
        scheduled_exit_trade_prices_verified=True,
        missing_daily_pages=json.loads((RUN / 'coverage.json').read_text())['missing_daily_pages'],
        verified_run=str(RUN), verification_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, sort_keys=True, indent=2) + '\n'
    path = OUT / 'verification.json'
    if path.exists():
        assert path.read_text() == text
    else:
        path.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
