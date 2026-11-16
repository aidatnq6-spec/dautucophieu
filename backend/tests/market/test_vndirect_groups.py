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


def hose_baskets(effective, vn30=("MBB", "VCB"), vn100=("MBB", "NEW", "VCB")):
    weights = {s: {"shares": "1000", "free_float": "0.50", "cap": "1.0000"} for s in vn30}
    return lambda: {"notice_id": 9, "title": "HOSE: Cập nhật danh mục cổ phiếu thành phần của Chỉ số quy mô VNAllshare kỳ tháng 10/2026",
                    "effective": effective, "period": "10/2026", "groups": {"VN30": list(vn30), "VN100": list(vn100), "weights": {"VN30": weights}}}


def saved_kept(tmp_path):
    out = tmp_path / "index-groups.json"
    out.write_text(json.dumps({"as_of": "2026-11-10", "source": "vndirect:finfo", "groups": {"VN30": ["MBB", "VCB"], "VN100": ["MBB", "OLD", "VCB"]},
                               "kept": {"VN100": "2026-11-10"}}), encoding="utf-8")
    return out


def test_vn100_comes_from_the_notice_of_hose_once_in_effect_and_a_change_is_told_once(tmp_path, capsys):
    out, sent = saved_kept(tmp_path), []
    # before the effective day: the old list stays kept, the new one is waiting
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 13), hose=hose_baskets(date(2026, 11, 16)), send=lambda t: sent.append(t) or True)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["groups"]["VN100"] == ["MBB", "OLD", "VCB"] and saved["kept"] == {"VN100": "2026-11-10"}
    assert saved["pending"] == {"VN100": {"effective": "2026-11-16", "notice_id": 9, "members": ["MBB", "NEW", "VCB"]}} and sent == []
    # from the effective day: the list of HOSE, dated and sourced, no longer kept by hand; one note with what came in and went out
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 16), hose=hose_baskets(date(2026, 11, 16)), send=lambda t: sent.append(t) or True)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["groups"]["VN100"] == ["MBB", "NEW", "VCB"] and saved["kept"] == {} and "pending" not in saved
    assert saved["group_sources"] == {"VN100": {"source": "hose", "notice_id": 9, "period": "10/2026", "effective": "2026-11-16"}}
    assert saved["vn30_weights"]["effective"] == "2026-11-16" and saved["vn30_weights"]["members"]["MBB"]["free_float"] == "0.50"
    assert sent == ["Rổ chỉ số HOSE thay đổi (thông báo HOSE kỳ 10/2026, hiệu lực 16/11/2026):\n- VN100: thêm NEW; bớt OLD\n"
                    "Danh sách theo dõi đã cập nhật nhóm chỉ số."]
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 17), hose=hose_baskets(date(2026, 11, 16)), send=lambda t: sent.append(t) or True)
    assert len(sent) == 1  # told once
    from investment_agent.market.watchlist import load_watchlist, vn100_review
    (tmp_path / "market-symbols.txt").write_text("MBB\n", encoding="utf-8")
    wl = load_watchlist(tmp_path)
    assert wl.kept == () and vn100_review(wl) is None and wl.group_dates["VN100"] == "2026-11-16"
    assert wl.group_sources == {"VN100": {"source": "hose", "notice_id": 9, "period": "10/2026", "effective": "2026-11-16"}}


def test_a_note_not_sent_waits_and_a_vn30_of_hose_differing_from_vndirect_is_reported(tmp_path, capsys):
    out = saved_kept(tmp_path)
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 16), hose=hose_baskets(date(2026, 11, 16), vn30=("MBB", "TCB")),
                 send=lambda t: False)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["note_pending"].startswith("Rổ chỉ số HOSE thay đổi")
    assert saved["vn30_check"] == {"hose": ["MBB", "TCB"], "vndirect": ["MBB", "VCB"], "notice_id": 9}
    sent = []
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 17), hose=hose_baskets(date(2026, 11, 16), vn30=("MBB", "TCB")),
                 send=lambda t: sent.append(t) or True)
    assert len(sent) == 1 and "note_pending" not in json.loads(out.read_text(encoding="utf-8"))


def test_a_failing_hose_source_keeps_the_saved_vn100_and_says_why(tmp_path, capsys):
    from investment_agent.market.providers.hose_baskets import BasketError
    out = saved_kept(tmp_path)

    def broken():
        raise BasketError("VN100 có 99 mã")
    index_groups(["VN30", "VN100"], out, get=get, today=date(2026, 11, 16), hose=broken, send=lambda t: True)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["groups"]["VN100"] == ["MBB", "OLD", "VCB"] and saved["kept"] == {"VN100": "2026-11-10"}
    assert json.loads(capsys.readouterr().out)["hose"] == {"status": "error", "reason": "VN100 có 99 mã"}
