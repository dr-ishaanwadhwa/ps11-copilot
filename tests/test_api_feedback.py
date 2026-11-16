"""Forecast what-if params and plainSummary on GET /api/v1/forecast.

Out-of-range what-if params are REJECTED with 422 (not clamped).
"""
import re

from fastapi.testclient import TestClient

from copilot.api.app import app

client = TestClient(app)
URL = "/api/v1/forecast"
EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿️]")


def _get(**params):
    params.setdefault("biz", "SME-1")
    params.setdefault("paths", 100)
    res = client.get(URL, params=params)
    assert res.status_code == 200, res.text
    return res.json()


def test_defaults_have_no_scenario():
    ps = _get()["plainSummary"]
    assert ps["scenarioActive"] is False
    assert ps["baselineLowestBalance"] is None
    assert ps["lowestBalance"] == _get()["lowestProjectedBalance"]
    assert ps["worstCaseLowestBalance"] <= ps["lowestBalance"]
    assert ps["headline"] and ps["detail"]


def test_receipt_delay_lowers_balance():
    base = _get()["plainSummary"]
    ps = _get(receipt_delay_days=15)["plainSummary"]
    assert ps["scenarioActive"] is True
    assert ps["baselineLowestBalance"] == base["lowestBalance"]
    assert ps["lowestBalance"] < ps["baselineLowestBalance"]


def test_monte_carlo_twin_accepts_params():
    res = client.get(f"{URL}/monte-carlo", params={"paths": 100, "sales_factor": 0.8})
    assert res.status_code == 200
    assert res.json()["plainSummary"]["scenarioActive"] is True


def test_out_of_range_rejected_422():
    for p in (
        {"receipt_delay_days": 61}, {"receipt_delay_days": -1},
        {"bill_shift_days": 31}, {"bill_shift_days": -31},
        {"sales_factor": 0.4}, {"sales_factor": 1.6},
    ):
        assert client.get(URL, params={"paths": 100, **p}).status_code == 422, p


def test_as_of_alias():
    a = _get(as_of="2026-08-31")
    b = _get(cutoff="2026-08-31")
    assert a["asOfDate"] == "2026-08-31"
    assert a["plainSummary"]["lowestBalance"] == b["plainSummary"]["lowestBalance"]
    assert _get()["asOfDate"] == "2026-09-30"


def test_no_emoji_in_summary():
    ps = _get(receipt_delay_days=10)["plainSummary"]
    for k in ("headline", "detail"):
        assert not EMOJI.search(ps[k]), ps[k]
        assert "P50" not in ps[k] and "Monte Carlo" not in ps[k]


def test_top_collection_matches_receivables():
    top = _get()["plainSummary"]["topCollectionAction"]
    custs = client.get("/api/v1/receivables", params={"biz": "SME-1"}).json()["customers"]
    best = max(custs, key=lambda c: c["totalOutstanding"])
    assert top["customerName"] == best["customerName"]
    assert top["outstanding"] == best["totalOutstanding"]
    assert top["oldestInvoiceDays"] == best["oldestInvoiceDays"]


def test_holdout_scores_are_real_and_sane():
    d = _get()
    assert 0 < d["holdoutMapeMeasured"] < 5
    assert 0 <= d["holdoutCoverageMeasured"] <= 1
    assert d["holdoutMapeMeasured"] != 0.118
