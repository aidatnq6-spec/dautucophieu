import json
from datetime import datetime, timedelta, timezone

from investment_agent.services.insider_alerts import insider_alerts_run

NOW = datetime(2026, 11, 2, 13, 0, tzinfo=timezone.utc)


def _page(*rows):
    return json.dumps({"data": [{"tagCodes": sym, "newsTitle": f"{sym}: {title}", "newsDate": day, "newsSource": "HOSE", "numberOfShares": shares,
                                 "transType": kind, "dstockUrl": f"https://dstock.vndirect.com.vn/tin-tuc/tin-tu-so/{i}"}
                                for i, (sym, day, kind, shares, title) in enumerate(rows)]})


OLD = ("ACB", "2026-06-18", "Mua", 15746000.0, "Báo cáo về thay đổi sở hữu của cổ đông lớn Nguyễn Thiên Hương Jenny và NCLQ")
NEW = ("ACB", "2026-11-01", "Đăng kí bán", 2219000.0, "Thông báo giao dịch cổ phiếu của người có liên quan của Người nội bộ Đặng Thu Hà")
STALE = ("ACB", "2026-08-01", "Bán", 1000.0, "Báo cáo kết quả giao dịch cổ phiếu của người nội bộ đăng muộn")


def test_first_run_records_a_baseline_then_new_notices_of_held_tickers_are_sent_once(tmp_path):
    pages = {"ACB": _page(OLD)}
    texts = []

    def get(url):
        return pages["ACB"] if "ACB" in url else _page()
    first = insider_alerts_run(tmp_path, held={"ACB"}, get=get, send=lambda t: texts.append(t) or True, now=NOW)
    assert first == {"status": "ok", "baseline": ["ACB"], "notices": 0, "sent": False, "errors": []} and texts == []
    pages["ACB"] = _page(NEW, STALE, OLD)
    later = NOW + timedelta(days=2)  # past the one-day cache
    out = insider_alerts_run(tmp_path, held={"ACB"}, get=get, send=lambda t: texts.append(t) or True, now=later)
    assert out["notices"] == 1 and out["sent"] is True  # a notice dated over 30 days back is recorded, not sent
    assert "Giao dịch nội bộ mới" in texts[0]
    assert "ACB · 01/11: Đăng ký bán 2.219.000 cp — Thông báo giao dịch cổ phiếu của người có liên quan của Người nội bộ Đặng Thu Hà" in texts[0]
    assert "https://dstock.vndirect.com.vn/tin-tuc/tin-tu-so/0" in texts[0] and "Không phải khuyến nghị" in texts[0]
    assert insider_alerts_run(tmp_path, held={"ACB"}, get=get, send=lambda t: texts.append(t) or True,
                              now=later + timedelta(days=2))["notices"] == 0  # once only


def test_a_failed_delivery_is_retried_and_tickers_no_longer_held_are_left_alone(tmp_path):
    pages = {"ACB": _page(OLD)}

    def get(url):
        return pages["ACB"]
    insider_alerts_run(tmp_path, held={"ACB"}, get=get, send=lambda t: True, now=NOW)
    pages["ACB"] = _page(NEW, OLD)
    later = NOW + timedelta(days=2)
    assert insider_alerts_run(tmp_path, held={"ACB"}, get=get, send=lambda t: False, now=later)["sent"] is False
    texts = []
    assert insider_alerts_run(tmp_path, held={"ACB"}, get=get, send=lambda t: texts.append(t) or True, now=later)["notices"] == 1
    assert insider_alerts_run(tmp_path, held=set(), get=get, send=lambda t: texts.append(t) or True, now=later)["notices"] == 0


def test_a_source_error_is_reported_per_ticker(tmp_path):
    def broken(url):
        raise RuntimeError("down")
    out = insider_alerts_run(tmp_path, held={"FPT"}, get=broken, send=lambda t: True, now=NOW)
    assert out["errors"] == ["FPT"] and out["baseline"] == []
