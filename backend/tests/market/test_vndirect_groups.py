import json
from datetime import date

from investment_agent.cli import index_groups, industries


def get(url: str) -> str:
    if "industry_classification" in url:
        return json.dumps({"data": [{"industryCode": "8300", "vietnameseName": "Ngân hàng", "codeList": "VCB,MBB,NEWB"},
                                    {"industryCode": "8600", "vietnameseName": "Bất động sản", "codeList": "HDG,KDH"},
                                    {"industryCode": "9500", "vietnameseName": "Công nghệ", "codeList": "NEWT"}]})
    if "indexCode:VN30" in url:
        return json.dumps({"data": [{"code": "VCB", "indexCode": "VN30"}, {"code": "MBB", "indexCode": "VN30"}]})
    if "indexCode:" in url:
        return json.dumps({"data": []})  # VNDirect marks VN30 members only
    raise AssertionError(url)


def test_sectors_keep_the_names_in_use_add_new_tickers_and_report_where_vndirect_differs(tmp_path, capsys):
    out = tmp_path / "industries.json"
    out.write_text(json.dumps({"as_of": "2026-11-10", "source": "vnstock:vci", "level": 2,
                               "sectors": {"VCB": "Ngân hàng", "HDG": "Điện, nước & xăng dầu khí đốt"}}), encoding="utf-8")
    (tmp_path / "hose-listing.json").write_text(json.dumps({"at": "2026-11-10T00:00:00+00:00", "listing": {
        "symbols": [], "icb_codes": {}, "icb_names": {"8300": "Ngân hàng", "8600": "Bất động sản", "9500": "Công nghệ Thông tin"}}}), encoding="utf-8")
    assert industries(["VCB", "HDG", "NEWB", "NEWT", "ZZZ"], out, get=get, today=date(2026, 11, 13)) == 0
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["sectors"] == {"HDG": "Điện, nước & xăng dầu khí đốt", "NEWB": "Ngân hàng", "NEWT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}
    assert saved["as_of"] == "2026-11-13" and saved["source"] == "vndirect:finfo"
    printed = json.loads(capsys.readouterr().out)
    assert printed["added"] == ["NEWB", "NEWT"] and printed["unclassified"] == ["ZZZ"]
    assert printed["differ"] == [{"symbol": "HDG", "kept": "Điện, nước & xăng dầu khí đốt", "vndirect": "Bất động sản"}]


def test_vn30_is_refreshed_and_vn100_kept_with_its_own_date(tmp_path, capsys):
    out = tmp_path / "index-groups.json"
    out.write_text(json.dumps({"as_of": "2026-11-10", "source": "vnstock:kbs", "groups": {"VN30": ["OLD"], "VN100": ["MBB", "OLD", "VCB", "X"]}}),
                   encoding="utf-8")
    assert index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 13)) == 0
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["groups"] == {"VN30": ["MBB", "VCB"], "VN100": ["MBB", "OLD", "VCB", "X"]}
    assert saved["kept"] == {"VN100": "2026-11-10"} and saved["as_of"] == "2026-11-13"
    assert json.loads(capsys.readouterr().out)["kept"] == {"VN100": "2026-11-10"}


def test_a_change_in_vn30_is_dated_and_kept_until_the_next_one(tmp_path, capsys):
    out = tmp_path / "index-groups.json"
    out.write_text(json.dumps({"as_of": "2026-11-10", "source": "vndirect:finfo", "groups": {"VN30": ["MBB", "VCB"], "VN100": ["MBB", "VCB", "X"]},
                               "kept": {"VN100": "2026-11-10"}}), encoding="utf-8")
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 13))
    assert "vn30_changed_on" not in json.loads(out.read_text(encoding="utf-8"))  # same members: no review seen
    saved = json.loads(out.read_text(encoding="utf-8"))
    saved["groups"]["VN30"] = ["OLD", "VCB"]
    out.write_text(json.dumps(saved), encoding="utf-8")
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 14))
    assert json.loads(out.read_text(encoding="utf-8"))["vn30_changed_on"] == "2026-11-14"
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 15))
    assert json.loads(out.read_text(encoding="utf-8"))["vn30_changed_on"] == "2026-11-14"  # unchanged since: the date stays


def test_the_watchlist_dates_each_group_and_says_when_vn100_may_be_out_of_date(tmp_path):
    from investment_agent.market.watchlist import load_watchlist, vn100_review
    (tmp_path / "market-symbols.txt").write_text("MBB\n", encoding="utf-8")
    (tmp_path / "index-groups.json").write_text(json.dumps({"as_of": "2026-11-13", "groups": {"VN30": ["MBB"], "VN100": ["MBB"]},
                                                            "kept": {"VN100": "2026-11-10"}, "vn30_changed_on": "2027-02-02"}), encoding="utf-8")
    wl = load_watchlist(tmp_path)
    assert wl.group_dates == {"VN30": "2026-11-13", "VN100": "2026-11-10"} and wl.kept == ("VN100",)
    assert vn100_review(wl) == {"vn30_changed_on": "2027-02-02", "vn100_as_of": "2026-11-10"}
    (tmp_path / "index-groups.json").write_text(json.dumps({"as_of": "2026-11-13", "groups": {"VN30": ["MBB"], "VN100": ["MBB"]},
                                                            "kept": {"VN100": "2026-11-10"}, "vn30_changed_on": "2026-08-04"}), encoding="utf-8")
    assert vn100_review(load_watchlist(tmp_path)) is None


def test_health_reminds_to_update_vn100_after_vn30_changed(tmp_path):
    from investment_agent.services.system_health import vn100_problem
    (tmp_path / "market-symbols.txt").write_text("MBB\n", encoding="utf-8")
    (tmp_path / "index-groups.json").write_text(json.dumps({"as_of": "2027-02-02", "groups": {"VN30": ["MBB"], "VN100": ["MBB"]},
                                                            "kept": {"VN100": "2026-11-10"}, "vn30_changed_on": "2027-02-02"}), encoding="utf-8")
    p = vn100_problem(tmp_path)
    assert p["id"] == "vn100_review" and "02/02/2027" in p["detail"] and "10/11/2026" in p["detail"]
