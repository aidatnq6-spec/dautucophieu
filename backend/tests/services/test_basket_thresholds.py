"""Ngưỡng nhắc theo giỏ chiến lược (spec 2026-11-24-nguong-theo-gio-design.md)."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from investment_agent.api.auth import OwnerContext
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.attention import attention_items
from investment_agent.services.baskets import RECORD, TradeBaskets, rule_label, rules_for
from investment_agent.services.drawdown import drawdown_run
from investment_agent.services.giveback import attention_lines, giveback_run

OWNER = OwnerContext("owner-1", "owner", "test")
KEY = "KDH@2026-10-02"


def repo_holding_kdh(settings=None):
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    repo.write(OWNER, "ledger_events", "main", {"events": [
        {"event_id": "d1", "type": "deposit", "effective_at": "2026-10-01", "sequence": 0, "amount": "500000000"},
        {"event_id": "b1", "type": "buy", "effective_at": "2026-10-02", "sequence": 0, "security_id": "KDH", "quantity": 1000, "price": "30000",
         "fee": "0", "tax": "0"}], "amendments": []}, expected_version=0, request_id="l1")
    repo.write(OWNER, "settings", "portfolio", {"concentration_limit": "0.25", "journal_review_threshold": "0.15", "drawdown_threshold": "0.3",
                                                **(settings or {})}, expected_version=0, request_id="s1")
    return repo


def basket(repo, *, drawdown=None, giveback=None, tag=True, version=0):
    b = {"id": "b1", "name": "Ngắn hạn", **({"drawdown": drawdown} if drawdown else {}), **({"giveback": giveback} if giveback else {})}
    repo.write(OWNER, *RECORD, {"baskets": [b], "tags": {KEY: "b1"} if tag else {}}, expected_version=version, request_id=f"k{version}")


def test_an_older_basket_without_rules_reads_as_the_common_level():
    data = TradeBaskets.model_validate({"baskets": [{"id": "b1", "name": "Dài hạn"}], "tags": {}})
    assert data.model_dump(mode="json")["baskets"][0]["drawdown"] == {"mode": "default", "threshold": None}
    assert data.model_dump(mode="json")["baskets"][0]["giveback"] == {"mode": "default", "min_gain": None, "share": None}


@pytest.mark.parametrize("rule", [
    {"drawdown": {"mode": "custom"}},
    {"drawdown": {"mode": "custom", "threshold": "0.005"}},
    {"drawdown": {"mode": "custom", "threshold": "0.96"}},
    {"giveback": {"mode": "custom", "min_gain": "0.2"}},
    {"giveback": {"mode": "custom", "min_gain": "0.2", "share": "1.5"}},
    {"giveback": {"mode": "custom", "min_gain": "11", "share": "0.5"}},
])
def test_a_custom_level_must_be_whole_and_within_the_common_limits(rule):
    with pytest.raises(ValidationError):
        TradeBaskets.model_validate({"baskets": [{"id": "b1", "name": "A", **rule}], "tags": {}})


def test_each_held_ticker_takes_its_baskets_level_or_the_common_one():
    repo = repo_holding_kdh({"giveback_min_gain": "0.3", "giveback_share": "0.5"})
    assert rules_for(repo, OWNER)["KDH"] == {
        "drawdown": {"source": "default", "basket": None, "threshold": "0.3"},
        "giveback": {"source": "default", "basket": None, "min_gain": "0.3", "share": "0.5"}}
    basket(repo, drawdown={"mode": "custom", "threshold": "0.07"}, giveback={"mode": "off"})
    rules = rules_for(repo, OWNER)["KDH"]
    assert rules["drawdown"] == {"source": "basket", "basket": "Ngắn hạn", "threshold": "0.07"}
    assert rules["giveback"] == {"source": "off", "basket": "Ngắn hạn", "min_gain": None, "share": None}
    assert rule_label(rules["drawdown"], "drawdown") == "giỏ Ngắn hạn: 7%"
    assert rule_label(rules["giveback"], "giveback") == "giỏ Ngắn hạn: không nhắc"
    assert rule_label({"source": "default", "basket": None, "threshold": "0.3"}, "drawdown") == "mức chung: 30%"
    assert rule_label({"source": "default", "basket": None, "min_gain": None, "share": None}, "giveback") == "mức chung: chưa đặt"
    assert rule_label({"source": "default", "basket": "Dài hạn", "min_gain": "0.3", "share": "0.5"}, "giveback") == "mức chung: lãi từ 30%, trả lại từ 50%"


def test_a_tag_that_no_longer_matches_a_period_takes_the_common_level():
    repo = repo_holding_kdh()
    repo.write(OWNER, *RECORD, {"baskets": [{"id": "b1", "name": "Ngắn hạn", "drawdown": {"mode": "custom", "threshold": "0.07"}}],
                                "tags": {"KDH@2026-09-01": "b1"}}, expected_version=0, request_id="k0")
    assert rules_for(repo, OWNER)["KDH"]["drawdown"]["source"] == "default"


def test_the_drawdown_reminder_follows_the_baskets_level_and_names_it(tmp_path):
    repo = repo_holding_kdh()
    SeriesStore(tmp_path / "trend-sources").upsert("KDH-1d", [(datetime(2026, 10, 26), "27")])  # −10%: inside 30%, past 7%
    sent = []
    assert drawdown_run(repo, OWNER, tmp_path, fetch=lambda *a: [], send=lambda t: sent.append(t) or True, request_id="r1")["alerts"] == 0
    basket(repo, drawdown={"mode": "custom", "threshold": "0.07"})
    assert drawdown_run(repo, OWNER, tmp_path, fetch=lambda *a: [], send=lambda t: sent.append(t) or True, request_id="r2")["alerts"] == 1
    assert "giỏ Ngắn hạn: 7%" in sent[0] and "−10,0%" in sent[0] and "nên" not in sent[0].lower()


def test_a_basket_that_does_not_remind_drops_the_ticker_and_reminds_again_once_turned_back_on(tmp_path):
    repo = repo_holding_kdh()
    SeriesStore(tmp_path / "trend-sources").upsert("KDH-1d", [(datetime(2026, 10, 26), "15")])  # −50%
    run = lambda rid: drawdown_run(repo, OWNER, tmp_path, fetch=lambda *a: [], send=lambda t: True, request_id=rid)["alerts"]  # noqa: E731
    assert run("r1") == 1 and run("r2") == 0
    basket(repo, drawdown={"mode": "off"})
    assert run("r3") == 0
    assert repo.read(OWNER, "settings", "drawdown_alerts").payload["alerted"] == []
    basket(repo, drawdown={"mode": "default"}, version=1)
    assert run("r4") == 1


def test_the_giveback_reminder_follows_the_baskets_levels_even_with_no_common_level(tmp_path):
    repo = repo_holding_kdh()
    SeriesStore(tmp_path / "trend-sources").upsert("KDH-1d", [(datetime(2026, 10, 2), "30"), (datetime(2026, 10, 3), "45"),
                                                              (datetime(2026, 10, 5), "33")])
    today, sent = date(2026, 10, 20), []
    assert giveback_run(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, request_id="g1", today=today)["holdings"] == 0
    basket(repo, giveback={"mode": "custom", "min_gain": "0.3", "share": "0.5"})
    assert giveback_run(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, request_id="g2", today=today)["holdings"] == 1
    assert "giỏ Ngắn hạn: lãi từ 30%, trả lại từ 50%" in sent[0]
    assert [k for k, *_ in attention_lines(repo, OWNER, tmp_path, today=today)] == ["giveback"]


def test_a_basket_that_does_not_remind_silences_the_common_giveback_level(tmp_path):
    repo = repo_holding_kdh({"giveback_min_gain": "0.3", "giveback_share": "0.5"})
    SeriesStore(tmp_path / "trend-sources").upsert("KDH-1d", [(datetime(2026, 10, 2), "30"), (datetime(2026, 10, 3), "45"),
                                                              (datetime(2026, 10, 5), "33")])
    basket(repo, giveback={"mode": "off"})
    assert giveback_run(repo, OWNER, tmp_path, send=lambda t: True, request_id="g1", today=date(2026, 10, 20))["holdings"] == 0
    assert attention_lines(repo, OWNER, tmp_path, today=date(2026, 10, 20)) == []


def test_attention_lists_the_drawdown_at_the_baskets_level(tmp_path):
    repo = repo_holding_kdh()
    data = tmp_path / "data"
    data.mkdir()
    SeriesStore(data / "trend-sources").upsert("KDH-1d", [(datetime(2026, 11, 6), "27")])
    now = datetime(2026, 11, 9, 1, 0)
    assert not [i for i in attention_items(repo, OWNER, data, now=now.astimezone()) if i["kind"] == "drawdown"]
    basket(repo, drawdown={"mode": "custom", "threshold": "0.07"})
    (item,) = [i for i in attention_items(repo, OWNER, data, now=now.astimezone()) if i["kind"] == "drawdown"]
    assert "giỏ Ngắn hạn: 7%" in item["text"]
