import json
from datetime import datetime, timezone

from investment_agent.market.plans_cafef import PlanStore, parse_plan, sync_plans


def page(symbol, year, *values):
    return json.dumps({"Data": {"Symbol": symbol, "Year": year, "Id": 1, "Values": [{"Code": None, "Name": n, "Value": v} for n, v in values]},
                       "Message": None, "Success": True})


def test_amounts_in_ty_dong_are_read_and_text_or_n_a_is_kept_as_written():
    out = parse_plan(page("PNJ", 2026, ("Doanh thu", "48.660,13 tỷ"), ("Lợi nhuận trước thuế", "4.270,97 tỷ"), ("Lợi nhuận sau thuế", "3.409 tỷ"),
                          ("Cổ tức bằng tiền mặt", "N/A")), symbol="PNJ")
    assert out == {"year": "2026", "revenue": "48660.13", "pbt": "4270.97", "npat": "3409",
                   "raw": {"Doanh thu": "48.660,13 tỷ", "Lợi nhuận trước thuế": "4.270,97 tỷ", "Lợi nhuận sau thuế": "3.409 tỷ", "Cổ tức bằng tiền mặt": "N/A"}}
    hpg = parse_plan(page("HPG", 2026, ("Doanh thu", "210.000 tỷ"), ("Lợi nhuận trước thuế", "N/A"), ("Lợi nhuận sau thuế", "22.000 tỷ")), symbol="HPG")
    assert (hpg["revenue"], hpg["pbt"], hpg["npat"]) == ("210000", None, "22000")


def test_a_page_for_another_ticker_or_without_figures_gives_nothing():
    assert parse_plan(page("FPT", 2026, ("Doanh thu", "1 tỷ")), symbol="HPG") is None
    assert parse_plan(page("VCB", 2026, ("Tín dụng", "Tăng ~10%")), symbol="VCB") is None
    assert parse_plan(json.dumps({"Data": None, "Success": False}), symbol="HPG") is None


NOW = datetime(2026, 11, 7, 13, tzinfo=timezone.utc)


def test_sync_keeps_each_year_seen_and_refreshes_after_a_week(tmp_path):
    store, urls = PlanStore(tmp_path), []

    def get(url):
        urls.append(url)
        return page("HPG", 2026, ("Doanh thu", "210.000 tỷ"), ("Lợi nhuận sau thuế", "22.000 tỷ"))
    store.save({"symbol": "HPG", "fetched_at": "2026-01-02T00:00:00+00:00", "source": "cafef", "years": {"2025": {"revenue": "150000"}}})
    assert sync_plans(store, ["HPG"], get=get, now=NOW, sleep=lambda s: None) == {"HPG": "ok"}
    rec = store.read("HPG")
    assert set(rec["years"]) == {"2025", "2026"} and rec["years"]["2026"]["npat"] == "22000" and rec["years"]["2026"]["read_on"] == "2026-11-07"
    assert urls == ["https://cafef.vn/du-lieu/Ajax/PageNew/KeHoachKinhDoanh.ashx?Symbol=HPG"]
    assert sync_plans(store, ["HPG"], get=get, now=NOW, sleep=lambda s: None) == {} and len(urls) == 1  # fresh: left alone


def test_sync_reports_a_ticker_without_a_plan_and_goes_on(tmp_path):
    store = PlanStore(tmp_path)

    def get(url):
        if "VCB" in url:
            return page("VCB", 2026, ("Tín dụng", "Tăng ~10%"))
        return page("FPT", 2026, ("Doanh thu", "58.580 tỷ"), ("Lợi nhuận trước thuế", "11.629 tỷ"))
    out = sync_plans(store, ["VCB", "FPT"], get=get, now=NOW, sleep=lambda s: None)
    assert out == {"FPT": "ok", "VCB": "no_figures"} and store.read("VCB")["years"] == {}


def test_cli_plans_sync_reads_the_watchlist(tmp_path, capsys):
    from investment_agent.cli import plans_sync
    (tmp_path / "market-symbols.txt").write_text("HPG" + chr(10), encoding="utf-8")
    assert plans_sync(tmp_path, get=lambda url: page("HPG", 2026, ("Doanh thu", "210.000 tỷ")), now=NOW, sleep=lambda s: None) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "ok", "results": {"HPG": "ok"}}
    assert PlanStore(tmp_path / "annual-plans-cafef").read("HPG")["years"]["2026"]["revenue"] == "210000"
