"""Tier: 2. Pins and refusal contracts for HFR percentile calculations.
Inputs: synthetic vintage workbooks/return records; outputs: assertions.
Identity: independent hand calculations and identical frozen reruns.
Run: PYTHONPATH=scripts/data_collection pytest tests/test_hfr_percentiles.py
"""

import io
import math
import sys
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/data_collection"))
import build_hfr_percentiles as h


def test_contract():
    assert h.CONTRACT["ror_divisor"] == 100
    assert h.CONTRACT["horizons"] == [12, 36, 60]
    assert h.CONTRACT["minimum_peers"] == 8
    assert h.CONTRACT["risk_free"] == "zero_hurdle_not_cash_adjusted"


def test_compound_volatility_drawdown_pins():
    # Wealth: 1 -> 1.10 -> .99 -> 1.188. Mean .0666667;
    # sample variance: ((.1-1/15)^2+(-.1-1/15)^2+(.2-1/15)^2)/2.
    out = h.metric_values([0.1, -0.1, 0.2])
    assert out["cumulative"] == pytest.approx(0.188)
    assert out["cagr"] == pytest.approx(1.188**4 - 1)
    assert out["max_drawdown"] == pytest.approx(-0.1)
    variance = ((0.1 - 1 / 15) ** 2 + (-0.1 - 1 / 15) ** 2 + (0.2 - 1 / 15) ** 2) / 2
    assert out["volatility"] == pytest.approx(math.sqrt(variance * 12))
    assert out["zero_hurdle_ratio"] == pytest.approx((1 / 15) / math.sqrt(variance) * math.sqrt(12))
    assert out["downside_deviation"] == pytest.approx(0.2)


def test_initial_loss_zero_volatility_and_total_loss():
    assert h.metric_values([-0.2, 0.25])["max_drawdown"] == pytest.approx(-0.2)
    assert h.metric_values([0] * 12)["zero_hurdle_ratio"] is None
    assert h.metric_values([0] * 11 + [-1])["cagr"] == -1
    assert h.metric_values([0] * 11 + [-1])["max_drawdown"] == -1
    assert h.metric_values([-0.999]) is not None


@pytest.mark.parametrize("values", [[], [None], [float("nan")], [float("inf")], [-1.001]])
def test_refuse_bad_return(values):
    assert h.metric_values(values) is None


def test_percentile_ties_direction_and_small_n():
    p, n = h.percentiles(dict(enumerate([1, 2, 2, 4, 5, 6, 7, 8])))
    assert n == 8 and p[0] == 0 and p[7] == 100
    assert p[1] == p[2] == pytest.approx(100 * 1.5 / 7)
    low, _ = h.percentiles(dict(enumerate([1, 2, 3, 4, 5, 6, 7, 8])), higher=False)
    assert low[0] == 100 and low[7] == 0
    assert h.percentiles({"a": 1, "b": 2}) == ({}, 2)


def test_missing_month_and_future_refusal():
    assert h.trailing_values({1: 0.1, 3: 0.3, 4: 100}, 3, 3) is None
    assert h.trailing_values({1: 0.1, 2: 0.2, 3: 0.3, 4: 100}, 3, 3) == [0.1, 0.2, 0.3]
    assert h.cutoff_for(
        {"vendor_datestamp": "2026-09-15", "delivery_date_proxy": "2026-09-16"}
    ) == date(2026, 8, 31)
    assert h.cutoff_for(
        {"vendor_datestamp": "2026-03-01", "delivery_date_proxy": "2026-02-28"}
    ) == date(2026, 1, 31)


def test_excel_dates():
    assert h.excel_date(41486) == date(2013, 7, 31)
    assert h.excel_date(1, 1) == date(1904, 1, 2)
    assert h.excel_date("bad") is None


def test_duplicate_conflicts_cannot_be_repaired_by_last_row():
    panel = {}
    assert h.put_observation(panel, ("a", "2020-01-31"), 0.1, {"row": 2}) == "new"
    assert h.put_observation(panel, ("a", "2020-01-31"), 0.1, {"row": 3}) == "duplicate"
    assert h.put_observation(panel, ("a", "2020-01-31"), 0.2, {"row": 4}) == "conflict"
    h.put_observation(panel, ("a", "2020-01-31"), 0.1, {"row": 5})
    assert panel[("a", "2020-01-31")]["conflict"]
    assert panel[("a", "2020-01-31")]["value"] is None
    assert len(panel[("a", "2020-01-31")]["sources"]) == 4


def test_representative_ignores_return_and_prefers_long_history():
    rows = [
        {"fund_id": "10", "contiguous_months": 40, "selection_assets": 100, "cagr_36": -0.8},
        {"fund_id": "11", "contiguous_months": 39, "selection_assets": 10000, "cagr_36": 3},
    ]
    assert h.representative(rows)["fund_id"] == "10"
    rows[1]["contiguous_months"] = 40
    assert h.representative(rows)["fund_id"] == "11"
    rows[1]["selection_assets"] = 100
    assert h.representative(rows)["fund_id"] == "10"


def test_persistence_excludes_current():
    rows = [
        {
            "quarter": q,
            "peer_group": "Activist",
            "firm_id": "1",
            "fund_id": f,
            "primary_top_quartile": t,
        }
        for q, f, t in [("2020Q1", "1", True), ("2020Q2", "1", False), ("2020Q3", "2", True)]
    ]
    h.add_persistence(rows)
    assert rows[0]["prior_top_quartile_share"] is None
    assert rows[1]["prior_top_quartile_share"] == 1
    assert rows[2]["prior_top_quartile_share"] == 0.5
    assert rows[2]["representative_changed_since_prior_observation"]


def xlsx_bytes(rows):
    buf = io.BytesIO()
    with ZipFile(buf, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="'
            + h.NS["m"]
            + '" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Returns" r:id="r1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        cells = []
        for rownum, row in enumerate(rows, 1):
            cells.append(
                '<row r="'
                + str(rownum)
                + '">'
                + "".join(
                    '<c r="'
                    + chr(65 + i)
                    + str(rownum)
                    + '" t="inlineStr"><is><t>'
                    + str(v)
                    + "</t></is></c>"
                    for i, v in enumerate(row)
                )
                + "</row>"
            )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="'
            + h.NS["m"]
            + '"><sheetData>'
            + "".join(cells)
            + "</sheetData></worksheet>",
        )
    return buf.getvalue()


def test_xlsx_source_rows_and_snapshot_separation():
    old = xlsx_bytes([["Fund_ID", "Date", "ROR"], ["1", "41486", "1.0"]])
    new = xlsx_bytes([["Fund_ID", "Date", "ROR"], ["1", "41486", "2.0"]])
    a = list(h.workbook_rows(old, "old.xlsx"))
    b = list(h.workbook_rows(new, "new.xlsx"))
    assert a[0][:3] == ("Returns", 2, 0)
    assert float(a[0][3]["ROR"]) / 100 == 0.01
    assert float(b[0][3]["ROR"]) / 100 == 0.02
    assert float(list(h.workbook_rows(old, "old.xlsx"))[0][3]["ROR"]) / 100 == 0.01


def test_deterministic_outputs_and_changed_freeze_refusal(tmp_path):
    p = tmp_path / "panel.csv.gz"
    h.write_csv(p, [{"id": "01", "return": 0.1, "sources": [{"row": 2}]}])
    before = p.read_bytes()
    h.write_csv(p, [{"id": "01", "return": 0.1, "sources": [{"row": 2}]}])
    assert p.read_bytes() == before
    with pytest.raises(ValueError):
        h.write_csv(p, [{"id": "01", "return": 0.2}])


def test_manager_join_and_rank_denominators():
    funds = []
    for i in range(8):
        funds.append(
            {
                "quarter": "2020Q1",
                "ranking_base_eligible": True,
                "fund_id": str(i),
                "firm_id": str(i),
                "sub_strategy": "Activist",
                "contiguous_months": 36,
                "selection_assets": 1,
                "cagr_36": i / 100,
            }
        )
    duplicate = dict(funds[0], fund_id="99", contiguous_months=35, cagr_36=10)
    ranked, cov = h.ranking_rows(funds + [duplicate], "manager")
    activist = [r for r in ranked if r["peer_group"] == "Activist"]
    assert len(activist) == 8
    assert all(r["cagr_36_peer_n"] == 8 for r in activist)
    assert next(r for r in activist if r["firm_id"] == "0")["fund_id"] == "0"
    assert sum(r["primary_top_quartile"] for r in activist) == 2
    assert next(c for c in cov if c["peer_group"] == "Activist")["base_eligible_products"] == 9
