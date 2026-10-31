import json
from datetime import date, datetime, timezone

from investment_agent.market.beta import BetaStore, fetch_betas
from investment_agent.market.company_people import PeopleStore, company_people
from investment_agent.valuation.capm import capm


def test_betas_for_the_whole_watchlist_come_in_one_call_and_bad_rows_are_dropped(tmp_path):
    urls = []

    def get(url):
        urls.append(url)
        return json.dumps({"data": [{"code": "FPT", "reportDate": "2026-10-30", "value": 0.7344580000710823},
                                    {"code": "HPG", "reportDate": "2026-10-30", "value": None}, {"code": "ZZZ", "reportDate": "2026-10-30", "value": 1.0}]})

    store = BetaStore(tmp_path)
    assert fetch_betas(store, ["FPT", "HPG"], get=get) == {"status": "ok", "betas": 1, "missing": ["HPG"]}
    assert len(urls) == 1 and "where=code:FPT,HPG" in urls[0] and "ratioCode:BETA" in urls[0]
    assert store.read()["values"] == {"FPT": {"beta": "0.7344580000710823", "date": "2026-10-30"}}


def test_capm_adds_beta_times_premium_to_the_risk_free_rate_or_says_what_is_missing():
    assert capm(rf="4.49", beta="0.73", erp="7.8") == {"ke": "0.1018", "reason": None}  # 4,49% + 0,73 × 7,8%
    assert capm(rf="4.49", beta=None, erp="7.8")["reason"] == "Chưa có beta của mã"
    assert capm(rf=None, beta="1", erp="7.8")["reason"] == "Chưa có lợi suất trái phiếu 10 năm"
    assert capm(rf="4.49", beta="1", erp=None)["reason"] == "Chưa nhập phần bù rủi ro (ERP) trong Cài đặt"


def test_people_are_read_once_a_month_and_the_saved_copy_survives_a_failing_source(tmp_path):
    calls = []

    def fetch(symbol):
        calls.append(symbol)
        return {"shareholders": [{"name": "Trương Gia Bình", "type": "Individual", "quantity": 117347966, "percent": 0.0689, "updated": "2026-08-03"}],
                "officers": [{"name": "Trương Gia Bình", "position": "Chủ tịch Hội đồng Quản trị", "percent": 0.0689, "quantity": 117347966}]}

    store = PeopleStore(tmp_path)
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    first = company_people(store, "FPT", fetch=fetch, now=now)
    assert first["shareholders"][0]["name"] == "Trương Gia Bình" and first["fetched_at"] == now.isoformat() and first["stale"] is False
    company_people(store, "FPT", fetch=fetch, now=datetime(2026, 11, 20, tzinfo=timezone.utc))
    assert calls == ["FPT"]  # cached for 30 days

    def broken(symbol):
        raise RuntimeError("down")
    later = company_people(store, "FPT", fetch=broken, now=datetime(2026, 12, 15, tzinfo=timezone.utc))
    assert later["stale"] is True and later["shareholders"][0]["name"] == "Trương Gia Bình"
    assert company_people(PeopleStore(tmp_path / "empty"), "HPG", fetch=broken, now=now)["reason"] == "Không đọc được dữ liệu cổ đông (nguồn lỗi)"


def test_cli_beta_sync_reads_the_watchlist(tmp_path, capsys):
    from investment_agent.cli import beta_sync
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    assert beta_sync(tmp_path, get=lambda url: json.dumps({"data": [{"code": "FPT", "reportDate": "2026-10-30", "value": 0.73}]})) == 0
    assert json.loads(capsys.readouterr().out)["betas"] == 1 and BetaStore(tmp_path).read()["values"]["FPT"]["beta"] == "0.73"


def test_others_is_what_the_ten_largest_holders_leave_and_old_cache_files_are_read_again(tmp_path):
    holders = [{"name": f"H{i}", "type": None, "quantity": None, "percent": p, "updated": None}
               for i, p in enumerate([0.0649, 0.0502, 0.0499, 0.0343, 0.0362, 0.0251, 0.018, 0.0184, 0.0172, 0.0156, 0.0125])]
    store = PeopleStore(tmp_path)
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    store.save("ACB", {"symbol": "ACB", "shareholders": [], "officers": [], "fetched_at": now.isoformat(), "source": "vnstock:vci"})  # before ownership
    calls = []

    def fetch(symbol):
        calls.append(symbol)
        return {"shareholders": holders, "officers": [], "ownership": None, "structure": None}
    view = company_people(store, "ACB", fetch=fetch, now=now)
    assert calls == ["ACB"] and view["others_percent"] == "0.6702"  # 1 − top ten; the eleventh (1,25%) is inside "others"
    blank = [{**holders[0], "percent": None}] + holders[1:3]
    assert company_people(PeopleStore(tmp_path / "b"), "ACB", fetch=lambda s: {"shareholders": blank, "officers": [], "ownership": None,
                                                                              "structure": None}, now=now)["others_percent"] is None


def test_a_holder_listed_twice_keeps_only_the_latest_disclosure(tmp_path):
    rows = [{"name": "Nguyễn Thiên Hương Jenny", "type": "Individual", "quantity": 151421326, "percent": 0.0295, "updated": "2026-06-19"},
            {"name": "Nguyễn Thiên Hương Jenny", "type": "Individual", "quantity": 60012110, "percent": 0.01344, "updated": "2024-09-13"},
            {"name": "Sather Gate Investments Limited", "type": "Organization", "quantity": 1, "percent": 0.0499, "updated": None}]
    view = company_people(PeopleStore(tmp_path), "ACB", fetch=lambda s: {"shareholders": rows, "officers": [], "ownership": None, "structure": None},
                          now=datetime(2026, 10, 31, tzinfo=timezone.utc))
    assert [(h["name"], h["percent"]) for h in view["shareholders"]] == [("Nguyễn Thiên Hương Jenny", 0.0295), ("Sather Gate Investments Limited", 0.0499)]
    assert view["others_percent"] == "0.9206"
