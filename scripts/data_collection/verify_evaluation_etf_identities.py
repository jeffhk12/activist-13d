"""Tier: 1. Retrieve exact-security ETF name intervals for candidate input dates.
Inputs: five fixed benchmark security IDs, WRDS names metadata. Outputs: coverage.
Identity: ticker/ETF/permno must agree and name intervals cover requested sessions.
No prices, returns, candidate outcomes or investor changes.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_evaluation_etf_identities.py
"""

import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze
from wrds_collect import FrozenClient, Refusal

OUT = ROOT / "research/runs/phase1-baseline/20260924-evaluation-inputs-etf-v1"
REQ = ROOT / "research/runs/phase1-baseline/20260924-evaluation-inputs-v1/requirements.json"
ETFS = {"SPY": 84398, "IWB": 88221, "IWM": 88222, "IWR": 89059, "IWV": 88223}


def main():
    req = json.loads(REQ.read_text())
    days = req["accountdays"]
    client = FrozenClient(online=True, cache=ROOT / "data/raw/wrds/evaluation-inputs-20260924-v1")
    records = []
    for symbol, permno in ETFS.items():
        try:
            payload, meta = client.request(
                "crsp.stocknames_v2", "GET", {"permno": permno, "limit": 1000, "offset": 0}
            )
            rows = payload.get("results")
            if (
                not isinstance(rows, list)
                or len(rows) >= 1000
                or payload.get("next")
                or any(r.get("permno") != permno for r in rows)
            ):
                raise ValueError("ETF_identity_request_not_verified")
            valid = [
                r for r in rows if r.get("ticker") == symbol and r.get("securitysubtype") == "ETF"
            ]
            covered = [d for d in days if any(r["namedt"] <= d <= r["nameenddt"] for r in valid)]
            records.append(
                dict(
                    symbol=symbol,
                    permno=permno,
                    status="full_interval_verified"
                    if len(covered) == len(days)
                    else "partial_or_missing_interval",
                    requested_sessions=len(days),
                    covered_sessions=len(covered),
                    first_uncovered=next((d for d in days if d not in covered), None),
                    last_verified_date=max(covered) if covered else None,
                    source=meta["cache_path"],
                    source_sha256=meta["sha256"],
                    records=valid,
                )
            )
            print(symbol, len(covered), "/", len(days), "identity sessions", flush=True)
        except (Refusal, ValueError) as error:
            records.append(
                dict(symbol=symbol, permno=permno, status="source_failure", reason=str(error))
            )
    freeze(OUT / "identity-coverage.json", encode(records))
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={str(REQ.relative_to(ROOT)): digest(REQ)},
                outputs={
                    p.name: digest(p)
                    for p in OUT.iterdir()
                    if p.is_file() and p.name != "provenance.json"
                },
            )
        ),
    )


if __name__ == "__main__":
    main()
