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
