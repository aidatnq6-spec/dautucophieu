import json
from datetime import date, datetime

from investment_agent.api.auth import OwnerContext
from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore
from investment_agent.services.thesis_model import check_lights

from signed_client import call
from test_deposit_book_route import client

B = 10**9
SCEN = [{"name": "bad", "price": "44106", "prob": "25"}, {"name": "base", "price": "58136", "prob": "50"}, {"name": "good", "price": "61362", "prob": "25"}]
IND = [{"id": "a", "name": "Lãi LD-LK quý", "tier": "lag", "unit": "tỷ", "bad": "73", "base": "88", "good": "103", "source": "auto:associates_q"},
       {"id": "b", "name": "Hiệu suất", "tier": "coincident", "unit": "%", "bad": "60.1", "base": "66.4", "good": "72.7", "source": "manual",
        "readings": [{"period": "2026-Q3", "value": "59"}]}]


def setup(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("PHP\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "x", "source": "t", "level": 2, "sectors": {"PHP": "Công nghiệp"}}), encoding="utf-8")
    StatementStore(tmp_path / "statements").save({"symbol": "PHP", "years": {}, "quarters": {"2026-Q3": {"associates": str(112 * B), "revenue": str(500 * B),
                                                                                                       "gross_profit": str(250 * B), "npat_parent": str(300 * B)}}})
    SeriesStore(tmp_path / "trend-sources").upsert("PHP-1d", [(datetime(2027, 1, 14), "44.4")])
    return client(tmp_path)


def test_scenarios_and_indicators_are_saved_and_graded_with_the_published_figures(tmp_path):
    c, clock = setup(tmp_path)
    assert call(c, clock, "GET", "/internal/stock/PHP/model").json()["version"] == 0
    body = call(c, clock, "PUT", "/internal/stock/PHP/model", {"scenarios": SCEN, "review": {"when": "khi có số 2027", "on": "2027-01-10"},
                                                               "indicators": IND, "expected_version": 0, "request_id": "tm1"}).json()
    assert body["version"] == 1 and body["scenarios"]["expected"] == "55435" and body["scenarios"]["upside"] == "0.2485"
    rows = {r["id"]: r for r in body["indicators"]}
    assert rows["a"]["current"] == "112" and rows["a"]["period"] == "2026-Q3" and rows["a"]["grade"] == "good"
    assert rows["b"]["grade"] == "bad" and body["lights"] == {"good": 1, "watch": 0, "bad": 1, "none": 0}
    bad = call(c, clock, "PUT", "/internal/stock/PHP/model", {"scenarios": [{**SCEN[0], "prob": "30"}, SCEN[1], SCEN[2]], "indicators": [],
                                                              "expected_version": 1, "request_id": "tm2"})
    assert bad.status_code == 422 and "100%" in bad.json()["message"]
    assert call(c, clock, "GET", "/internal/stock/HPG/model").status_code == 404

    owner, sent = OwnerContext(uid="owner-1", role="owner", correlation_id="t"), []
    out = check_lights(c.app.state.personal_repository, owner, tmp_path, send=lambda t: sent.append(t) or True, today=date(2027, 1, 15), request_id="lights1")
    assert out == {"status": "ok", "lines": 2, "sent": True} and "Hiệu suất 59 % (2026-Q3) chạm mức Xấu 60.1" in sent[0] and "xem lại kịch bản" in sent[0]
    again = check_lights(c.app.state.personal_repository, owner, tmp_path, send=lambda t: sent.append(t) or True, today=date(2027, 1, 15), request_id="lights2")
    assert again["sent"] is False and len(sent) == 1  # each once
