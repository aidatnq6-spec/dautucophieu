import json
from datetime import date, datetime
from decimal import Decimal

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



def test_questions_and_catalysts_are_saved_with_the_day_and_a_due_catalyst_is_sent_once(tmp_path):
    c, clock = setup(tmp_path)
    body = call(c, clock, "PUT", "/internal/stock/PHP/model", {"scenarios": [], "indicators": [], "stage": "draft",
        "questions": {"business": {"status": "good", "summary": "Tiền thuê chắc chắn", "gaps": [{"id": "g1", "text": "TEU quý từng cảng", "ref": "PHP-01"}]}},
        "catalysts": [{"id": "c1", "when": "Q4/2026", "on": "2027-01-10", "sign": "+", "text": "Bàn giao hạ tầng đợt 3", "source": "ĐHĐCĐ"}],
        "expected_version": 0, "request_id": "q1"}).json()
    assert body["gaps"] == {"open": 1, "total": 1} and body["updated_on"] == "2027-01-15" and body["catalysts_due"] == ["c1"]
    owner, sent = OwnerContext(uid="owner-1", role="owner", correlation_id="t"), []
    out = check_lights(c.app.state.personal_repository, owner, tmp_path, send=lambda t: sent.append(t) or True, today=date(2027, 1, 15), request_id="cat1")
    assert out["sent"] is True and "đến mốc Q4/2026 (+) Bàn giao hạ tầng đợt 3" in sent[0]



def test_the_page_fills_in_catalysts_suggested_indicators_facts_and_gaps_from_public_data(tmp_path):
    from investment_agent.market.corporate_events import EventStore
    c, clock = setup(tmp_path)
    quarters = {f"{y}-Q{q}": {"revenue": str((400 + 10 * i) * B), "gross_profit": str((150 + 3 * i) * B), "npat_parent": str((100 + 5 * i) * B),
                              "pbt": str((130 + 5 * i) * B), "associates": str((20 + i) * B)}
                for i, (y, q) in enumerate((y, q) for y in (2024, 2025, 2026) for q in (1, 2, 3, 4)) if (y, q) <= (2026, 3)}
    StatementStore(tmp_path / "statements").save({"symbol": "PHP", "years": {}, "quarters": quarters})
    EventStore(tmp_path).save("PHP", [{"id": "PHP-1.VN", "symbol": "PHP", "kind": "meeting", "title": "Họp - ĐHĐCĐ bất thường", "key_date": "2027-02-20",
                                      "exright": None, "record": None, "payout": None, "ratio": None, "value_per_share": None},
                                     {"id": "PHP-1.EN_GB", "symbol": "PHP", "kind": "meeting", "title": "Meeting - EGM", "key_date": "2027-02-20",
                                      "exright": None, "record": None, "payout": None, "ratio": None, "value_per_share": None}], fetched_at="2027-01-15T00:00:00+00:00")
    body = call(c, clock, "GET", "/internal/stock/PHP/model").json()
    auto = body["auto_catalysts"]
    assert [a["when"] for a in auto] == ["Q4/2026", "20/02/2027"] and all(a["sign"] == "?" for a in auto)  # Q4 report due, then the meeting
    assert "Hạn công bố báo cáo tài chính Q4/2026" in auto[0]["text"]
    sources = [s["source"] for s in body["suggested_indicators"]]
    assert sources[:3] == ["auto:npat_parent_q", "auto:revenue_q", "auto:gross_margin_q"]
    s = body["suggested_indicators"][0]
    assert float(s["bad"]) < float(s["base"]) <= float(s["good"])
    assert body["facts"]["business"][0].startswith("Doanh thu 4 quý đến Q3/2026:")
    assert any("Chưa có kế hoạch kinh doanh năm 2027" in g for g in body["auto_gaps"]["strategy"])
    kept = call(c, clock, "PUT", "/internal/stock/PHP/model", {"scenarios": [], "indicators": body["suggested_indicators"][:1],
                                                               "catalysts": [{**auto[1], "sign": "+"}], "expected_version": 0, "request_id": "keep1"}).json()
    assert [a["id"] for a in kept["auto_catalysts"]] == [auto[0]["id"]]  # the one kept is now the owner's
    assert "auto:npat_parent_q" not in [x["source"] for x in kept["suggested_indicators"]]


def test_insider_and_valuation_facts_read_as_sentences(tmp_path):
    from datetime import date as d

    from investment_agent.market.insider_deals import InsiderStore
    from investment_agent.services import thesis_auto
    InsiderStore(tmp_path).save("PHP", {"symbol": "PHP", "deals": [{"date": "2026-10-01", "kind": "Mua", "shares": 3000000, "source": None, "title": "", "url": None},
                                                                  {"date": "2026-09-01", "kind": "Bán", "shares": 1000000, "source": None, "title": "", "url": None}],
                                        "fetched_at": "2026-11-14T00:00:00+00:00"})
    (tmp_path / "industries.json").write_text('{"as_of": "x", "source": "t", "level": 2, "sectors": {}}', encoding="utf-8")
    f, _ = thesis_auto.facts(tmp_path, "PHP", {}, {}, pe=[Decimal(10)] * 30 + [Decimal(5)], pb=[], plans={}, lights={"good": 0, "watch": 0, "bad": 0, "none": 0},
                             today=d(2026, 11, 14))
    assert f["monitoring"] == ["Nội bộ 12 tháng: mua 3.000.000 CP (1 báo cáo), bán 1.000.000 CP (1 báo cáo)."]
    assert f["valuation"][0].endswith("thấp nhất trong 31 tháng.")
