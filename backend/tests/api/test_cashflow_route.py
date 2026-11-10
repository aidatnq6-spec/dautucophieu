import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cashflow_fixture import month_rows, workbook  # noqa: E402

from signed_client import call  # noqa: E402
from test_passive_income_route import client  # noqa: E402  (Clock: 2027-01-15; deposit rate 6%)


def send(c, clock, data, commit=False, version=0, rid="cf1"):
    return call(c, clock, "POST", "/internal/cashflow/import", {"content_base64": base64.b64encode(data).decode(), "commit": commit, "expected_version": version, "request_id": rid})


def test_a_preview_writes_nothing_and_saving_keeps_the_months(tmp_path):
    c, clock = client(tmp_path)
    r = send(c, clock, workbook(year=2026))
    assert r.status_code == 200 and r.json()["preview"]["months"][0] == "2026-01" and r.json()["version"] == 0
    assert call(c, clock, "GET", "/internal/cashflow").json()["months"] == []
    r = send(c, clock, workbook(year=2026), commit=True, rid="cf2")
    assert r.status_code == 200 and r.json()["version"] == 1 and len(r.json()["months"]) == 10


def test_a_bad_file_is_refused_and_a_large_one_is_accepted(tmp_path):
    c, clock = client(tmp_path)
    assert send(c, clock, b"nope").json()["code"] == "invalid_file"
    padded = workbook()[:-22] + b"\0" * 1_500_000 + workbook()[-22:]  # past the usual 1 MB limit, like a workbook with pictures
    assert send(c, clock, padded, rid="cf3").status_code in (200, 422)  # reached the parser rather than being cut off as too large


def test_imported_months_feed_lifestyle_and_the_three_levels(tmp_path):
    c, clock = client(tmp_path)
    call(c, clock, "PUT", "/internal/equity-budget", {"layers": {"deposit": "600000000", "bond": "0", "gold": "0", "crypto": "0"}, "reserve": "0", "expected_version": 0, "request_id": "eb1"})
    call(c, clock, "PUT", "/internal/wealth-check", {"income": "20000000", "expenses": "46000000", "birth_year": 1985, "expected_version": 0, "request_id": "wc1"})
    rows = {**{m: r for m, r in month_rows().items()}}
    send(c, clock, workbook(rows, year=2026), commit=True, rid="cf2")
    life = call(c, clock, "GET", "/internal/wealth-check").json()["lifestyle"]
    assert life["verdict"] is not None
    call(c, clock, "PUT", "/internal/passive-income", {"target": "10000000", "rate": None, "expected_version": 0, "request_id": "pi1"})
    levels = call(c, clock, "GET", "/internal/passive-income").json()["levels"]
    assert levels["actual"] == "23000000" and levels["actual_months"] == ["2026-08", "2026-09", "2026-10"]
    assert levels["rows"][0]["actual"] == "0.5000"  # 23 tr against the 46 tr spending entered at Sức khỏe tài chính
