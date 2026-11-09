import json
from datetime import date, datetime, timezone
from decimal import Decimal

from investment_agent.api.auth import OwnerContext
from investment_agent.market.financial_ratios import FinancialRatioStore
from investment_agent.market.leading import MacroStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository
from investment_agent.services.early_lights import catalog, color, lights_check, record_id, symbol_lights

OWNER = OwnerContext("owner-1", "owner", "test")
TODAY = date(2026, 11, 9)


def test_the_colour_follows_the_direction_the_thresholds_are_written_in():
    assert [color(Decimal(v), Decimal(55), Decimal(75)) for v in ("50", "55", "60", "75", "90")] == ["bad", "watch", "watch", "good", "good"]
    assert [color(Decimal(v), Decimal("1.5"), Decimal("0.9")) for v in ("2", "1.5", "1", "0.9", "0.5")] == ["bad", "watch", "watch", "good", "good"]  # a lower P/B is better


def setup(tmp_path, symbols="VCB\n", sectors=None):
    (tmp_path / "market-symbols.txt").write_text(symbols, encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "x", "source": "t", "level": 2, "sectors": sectors or {"VCB": "Ngân hàng"}}), encoding="utf-8")
    FinancialRatioStore(tmp_path / "financial-ratios").save({"symbol": "VCB", "kind": "bank", "fetched_at": "x", "source": "t",
                                                             "quarters": {"2026-06-30": {"BAD_LOANS_RATIO_AQ": "0.02"}, "2026-09-30": {"BAD_LOANS_RATIO_AQ": "0.0071"}}})
    MacroStore(tmp_path).upsert("wti", [(date(2026, 11, 6), "66")], entry="auto")
    MacroStore(tmp_path).upsert("com_rubber", [(date(2026, 1, 31), "120")], entry="auto")
    repo = PersonalRepository("owner-1", MemoryDocumentStore())
    return repo


def save(repo, rules, version=0, symbol="VCB"):
    repo.write(OWNER, "settings", record_id(symbol), {"rules": rules}, expected_version=version, request_id=f"r{version}")


def test_the_choice_of_indicators_suits_the_kind_of_company():
    ids = {c["id"]: c for c in catalog("bank")}
    assert ids["macro:wti"]["tier"] == "Dẫn dắt" and ids["stock:BAD_LOANS_RATIO_AQ"]["tier"] == "Kết quả" and ids["stock:pb_now"]["tier"] == "Định giá"
    assert "stock:gross_margin" not in ids and "stock:gross_margin" in {c["id"] for c in catalog(None)} and "stock:roic" in {c["id"] for c in catalog(None)}


def test_each_rule_shows_its_latest_value_in_percent_where_it_is_one_and_old_or_missing_data_gets_no_colour(tmp_path):
    repo = setup(tmp_path)
    save(repo, [{"id": "macro:wti", "bad": "55", "good": "75"}, {"id": "stock:BAD_LOANS_RATIO_AQ", "bad": "2", "good": "1"}, {"id": "macro:com_rubber", "bad": "100", "good": "150"},
                {"id": "stock:pe_now", "bad": "20", "good": "10"}])
    out = symbol_lights(repo, OWNER, tmp_path, "VCB", today=TODAY)
    rows = {r["id"]: r for r in out["rows"]}
    assert rows["macro:wti"]["state"] == "watch" and rows["macro:wti"]["value"] == "66" and rows["macro:wti"]["date"] == "2026-11-06"
    assert rows["stock:BAD_LOANS_RATIO_AQ"]["state"] == "good" and rows["stock:BAD_LOANS_RATIO_AQ"]["value"] == "0.71" and rows["stock:BAD_LOANS_RATIO_AQ"]["date"] == "2026-Q3"
    assert rows["macro:com_rubber"]["state"] == "none" and "cũ" in rows["macro:com_rubber"]["note"]  # nine months old: no colour from it
    assert rows["stock:pe_now"]["state"] == "none" and rows["stock:pe_now"]["value"] is None


def test_a_change_of_colour_is_announced_once_and_the_first_reading_is_only_remembered(tmp_path):
    repo = setup(tmp_path)
    save(repo, [{"id": "macro:wti", "bad": "55", "good": "75"}])
    sent = []
    assert lights_check(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, today=TODAY)["changes"] == 0 and sent == []
    MacroStore(tmp_path).upsert("wti", [(date(2026, 11, 7), "50")], entry="auto")
    out = lights_check(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, today=TODAY)
    assert out["changes"] == 1 and "VCB" in sent[0] and "Theo dõi → Xấu" in sent[0]
    assert lights_check(repo, OWNER, tmp_path, send=lambda t: sent.append(t) or True, today=TODAY)["changes"] == 0 and len(sent) == 1


def test_a_failed_send_is_tried_again_next_run(tmp_path):
    repo = setup(tmp_path)
    save(repo, [{"id": "macro:wti", "bad": "55", "good": "75"}])
    lights_check(repo, OWNER, tmp_path, send=lambda t: True, today=TODAY)
    MacroStore(tmp_path).upsert("wti", [(date(2026, 11, 7), "50")], entry="auto")
    assert lights_check(repo, OWNER, tmp_path, send=lambda t: False, today=TODAY)["sent"] is False
    assert lights_check(repo, OWNER, tmp_path, send=lambda t: True, today=TODAY)["changes"] == 1
