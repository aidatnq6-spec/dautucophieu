from datetime import date, datetime, timezone

from investment_agent.services.weekly_brief import compose, week_of, weekly_brief_run

SAT = date(2026, 10, 31)


def _brief(day, close, net):
    return {"session_date": day, "indices": {"status": "ok", "rows": [{"id": "VNINDEX", "status": "ok", "close": close}]},
            "hose": {"status": "ok", "foreign": {"net_value_bn": net}}}


INPUTS = {
    "series": [{"date": "2026-10-23", "portfolio": "110.00", "vnindex": "105.00"}, {"date": "2026-10-30", "portfolio": "112.20", "vnindex": "103.95"}],
    "briefs": {"2026-10-23": _brief("2026-10-23", "1760.00", "100"), "2026-10-27": _brief("2026-10-27", "1750.00", "-200.5"),
               "2026-10-28": _brief("2026-10-28", "1745.00", "-150"), "2026-10-30": _brief("2026-10-30", "1741.62", "-633.42")},
    "index": [(date(2026, 10, 23), 1760.0), (date(2026, 10, 30), 1741.62)],
    "closes": {"HPG": [(date(2026, 10, 23), 21.5), (date(2026, 10, 30), 21.0)], "SSI": [(date(2026, 10, 30), 19.3)]},
    "insider": {"HPG": [{"date": "2026-10-29", "kind": "Đăng kí mua", "shares": 1000000, "title": "Thông báo giao dịch của người nội bộ A",
                         "url": "https://dstock.vndirect.com.vn/tin-tuc/tin-tu-so/1"},
                        {"date": "2026-10-01", "kind": "Mua", "shares": 5, "title": "cũ", "url": None}]},
    "events": [{"symbol": "HPG", "kind": "dividend_cash", "key_date": "2026-11-04", "title": "Trả cổ tức bằng tiền - 500 đ/cp", "exright": "2026-11-04",
                "record": "2026-11-05", "payout": None, "value_per_share": 500.0, "id": "e1"},
               {"symbol": "HPG", "kind": "insider", "key_date": "2026-11-02", "title": "Đặng Ngọc Khánh - Đăng kí Bán 100,000 HPG", "exright": None,
                "record": None, "payout": None, "value_per_share": None, "id": "e3"},
               {"symbol": "FPT", "kind": "meeting", "key_date": "2026-11-20", "title": "FPT - ĐHCĐ bất thường", "exright": None, "record": None,
                "payout": None, "value_per_share": None, "id": "e2"}],
    "alerts": [{"symbol": "HPG", "op": "below", "price": "21", "triggered_at": "2026-10-30T03:30:00+00:00", "triggered_price": "20.95"},
               {"symbol": "VNINDEX", "op": "above", "price": "1800", "triggered_at": None, "triggered_price": None}],
}


def test_the_week_runs_monday_to_friday_before_the_weekend():
    assert week_of(SAT) == (date(2026, 10, 26), date(2026, 10, 30))
    assert week_of(date(2026, 11, 1)) == (date(2026, 10, 26), date(2026, 10, 30))


def test_brief_puts_the_portfolio_against_vnindex_then_foreign_flows_insiders_next_week_and_alerts():
    text = compose(**INPUTS, held={"HPG", "SSI"}, watched={"HPG", "SSI", "FPT"}, today=SAT)
    assert text.startswith("BẢN TIN TUẦN 26/10–30/10/2026")
    assert "Danh mục: +2,00% · VN-Index: −1,04% (1.741,62 điểm, tuần trước 1.760,00)" in text
    assert "Khối ngoại HOSE: bán ròng 983,9 tỷ đồng (3 phiên có số; thiếu 26/10, 29/10)" in text
    assert "HPG −2,33%" in text and "SSI: chưa có giá tuần trước" in text
    assert "HPG · 29/10: Đăng ký mua 1.000.000 cp — Thông báo giao dịch của người nội bộ A" in text and "cũ" not in text
    assert "HPG (đang nắm): Trả cổ tức bằng tiền · GDKHQ 04/11/2026 · 500 đ/cp · chốt 05/11/2026" in text
    assert "FPT" not in text.split("LỊCH TUẦN TỚI")[1].split("CẢNH BÁO")[0]  # 20/11 is beyond next week
    assert "Đặng Ngọc Khánh" not in text  # dividends, issues and meetings only, as the event reminders
    assert "HPG ≤ 21,00: đã báo 30/10 ở 20,95" in text and "1 cảnh báo đang chờ" in text
    assert text.rstrip().endswith("Không phải khuyến nghị.")


def test_missing_inputs_are_named_not_filled():
    text = compose(series=[], index=[], briefs={}, closes={}, insider={}, events=[], alerts=[], held=set(), watched=set(), today=SAT)
    assert "Danh mục: chưa đủ dữ liệu hiệu quả cho tuần này" in text
    assert "VN-Index: chưa có số phiên cuối tuần" in text
    assert "Khối ngoại HOSE: chưa có số" in text
    assert "Không có thông báo mới của mã đang nắm." in text and "Không có sự kiện đã biết." in text


def test_sent_once_a_week_on_the_weekend(tmp_path):
    texts = []
    compose_inputs = lambda: INPUTS | {"held": {"HPG"}, "watched": {"HPG"}}  # noqa: E731
    friday = datetime(2026, 10, 30, 13, tzinfo=timezone.utc)
    assert weekly_brief_run(tmp_path, inputs=compose_inputs, send=lambda t: texts.append(t) or True, now=friday)["status"] == "skipped"
    saturday = datetime(2026, 10, 31, 1, 30, tzinfo=timezone.utc)
    assert weekly_brief_run(tmp_path, inputs=compose_inputs, send=lambda t: False, now=saturday)["sent"] is False
    assert weekly_brief_run(tmp_path, inputs=compose_inputs, send=lambda t: texts.append(t) or True, now=saturday)["sent"] is True
    sunday = datetime(2026, 11, 1, 1, 30, tzinfo=timezone.utc)
    assert weekly_brief_run(tmp_path, inputs=compose_inputs, send=lambda t: texts.append(t) or True, now=sunday)["status"] == "already_sent"
    assert len(texts) == 1


def test_inputs_are_gathered_from_stored_data_without_touching_the_network(tmp_path):
    import json as _json

    from investment_agent.cli import weekly_inputs
    from investment_agent.market.series import SeriesStore
    (tmp_path / "market-symbols.txt").write_text("HPG\nFPT\n", encoding="utf-8")
    (tmp_path / "brief").mkdir()
    (tmp_path / "brief" / "2026-10-30.json").write_text(_json.dumps(_brief("2026-10-30", "1741.62", "-633.42")), encoding="utf-8")
    SeriesStore(tmp_path / "trend-sources").upsert("HPG-1d", [(datetime(2026, 10, 30), "21")])
    got = weekly_inputs(tmp_path, ledger_events=[], held={"HPG"}, alerts=[], insider=lambda s: [], today=SAT)
    assert set(got["briefs"]) == {"2026-10-30"} and got["closes"]["HPG"] == [(date(2026, 10, 30), 21.0)] and got["index"] == []
    assert got["watched"] == {"HPG", "FPT"} and got["series"] == [] and got["insider"] == {"HPG": []}
