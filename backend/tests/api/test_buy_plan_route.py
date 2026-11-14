from datetime import date, datetime

from investment_agent.market.series import SeriesStore
from investment_agent.services.buy_plan import check_plan

from signed_client import call
from test_deposit_book_route import client


def test_tranches_are_saved_shown_against_the_latest_close_and_met_once_by_the_check(tmp_path):
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(2027, 1, 14), "88")])
    c, clock = client(tmp_path)
    body = call(c, clock, "PUT", "/internal/buy-plan", {"tranches": [{"id": "a", "symbol": "FPT", "amount": "20000000", "kind": "price_le", "value": "90"},
                                                                      {"id": "b", "symbol": "FPT", "amount": "10000000", "kind": "date", "value": "2027-03-01"}],
                                                        "expected_version": 0, "request_id": "bp1"}).json()
    assert body["version"] == 1 and [t["status"] for t in body["tranches"]] == ["waiting", "waiting"]
    assert body["tranches"][0]["close"] == "88" and body["tranches"][0]["distance"] == "0.0227"
    sent = []
    from investment_agent.api.auth import OwnerContext
    owner = OwnerContext(uid="owner-1", role="owner", correlation_id="t")
    out = check_plan(c.app.state.personal_repository, owner, tmp_path, send=lambda text: sent.append(text) or True, today=date(2027, 1, 15), request_id="chk1")
    assert out == {"status": "ok", "met": 1, "sent": True, "waiting": 1} and "FPT: giá đóng cửa 88 ≤ 90" in sent[0]
    again = check_plan(c.app.state.personal_repository, owner, tmp_path, send=lambda text: sent.append(text) or True, today=date(2027, 1, 15), request_id="chk2")
    assert again["met"] == 0 and len(sent) == 1
    view = call(c, clock, "GET", "/internal/buy-plan").json()
    assert [t["status"] for t in view["tranches"]] == ["met", "waiting"]
    done = call(c, clock, "PUT", "/internal/buy-plan", {"tranches": [{**view["tranches"][0], "status": "done"}, view["tranches"][1]], "expected_version": 2,
                                                        "request_id": "bp2"}).json()
    assert [t["status"] for t in done["tranches"]] == ["done", "waiting"]
    bad = call(c, clock, "PUT", "/internal/buy-plan", {"tranches": [{"id": "z", "symbol": "FPT", "amount": "1", "kind": "price_le", "value": "-1"}],
                                                       "expected_version": 3, "request_id": "bp3"})
    assert bad.status_code == 422
