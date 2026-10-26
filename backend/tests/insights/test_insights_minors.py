import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from investment_agent.ai.catalog import load_catalog
from investment_agent.insights.download import fetch_pdf
from investment_agent.insights.run import due, record_status
from investment_agent.insights.sources import discover_acbs, discover_worldbank, safe_url, ssi_titles
from investment_agent.insights.store import InsightStore
from investment_agent.insights.telegram import send_new
from investment_agent.notifications.telegram import SendOutcome

NOW = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)


def test_only_plain_web_links_are_kept():
    assert safe_url("https://acbs.com.vn/a.pdf") == "https://acbs.com.vn/a.pdf"
    for bad in ("javascript:alert(1)//x", "data:text/html,x", "file:///c:/x.pdf", "https:///nohost", "  "):
        assert safe_url(bad) is None, bad


def test_sources_drop_reports_with_unsafe_links():
    listing = '<a href="javascript:alert(1)//trung-tam-phan-tich/chi-tiet/xau">x</a>'
    assert discover_acbs(lambda url: listing, since=date(2026, 8, 1)) == []
    wb = json.dumps({"documents": {"D1": {"docdt": "2026-09-30T00:00:00Z", "display_title": "Viet Nam Macro Monitoring", "docty": "Brief",
                                          "pdfurl": "javascript:alert(1)"}}})
    assert discover_worldbank(lambda url: wb, since=date(2026, 8, 1)) == []
    ssi = ('<a class="titlePost" href="javascript:void(0)">T</a><p><span>01/10/2026</span></p>'
           '<a href="/analysis-center/report/download/bao-cao"> Tải xuống </a>')
    assert ssi_titles(lambda url: ssi, limit=5)[0]["url"].startswith("https://www.ssi.com.vn/")


def test_corrupt_catalog_cache_is_refetched(tmp_path):
    cache = tmp_path / "catalog.json"
    cache.write_text("{broken", encoding="utf-8")
    payload = json.dumps({"data": [{"id": "m/a", "pricing": {"prompt": "0.0000001", "completion": "0.0000005"}}]})
    assert "m/a" in load_catalog(cache, lambda url: payload, now=NOW).models
    assert json.loads(cache.read_text(encoding="utf-8"))["fetched_at"] == NOW.isoformat()


def test_catalog_failure_is_recorded_for_the_page(tmp_path):
    record_status(tmp_path, now=NOW, out={"status": "stopped:catalog_unavailable", "processed": []})
    status = json.loads((tmp_path / "insights" / "status.json").read_text(encoding="utf-8"))
    assert status == {"at": NOW.isoformat(), "status": "stopped:catalog_unavailable", "processed": []}


def test_bad_status_file_means_due(tmp_path):
    (tmp_path / "insights").mkdir()
    for content in ('{"at": 5}', '{"at": null}', "[]", '"x"'):
        (tmp_path / "insights" / "status.json").write_text(content, encoding="utf-8")
        assert due(tmp_path, now=NOW, min_hours=6) is True, content


RECORD = {"source": "acbs", "ref_id": "r", "title": "t", "page_url": "https://acbs.com.vn/x", "status": "ok", "telegram_sent": False,
          "published": "2026-10-01", "insight": {}}
ON = SimpleNamespace(enabled=True, scheduled_enabled=True, chat_id="-1001234")


class Sender:
    def __init__(self, fail_on=()):
        self.sent, self.fail_on = [], set(fail_on)

    def send(self, chat_id, text):
        n = len(self.sent)
        self.sent.append(text)
        return SendOutcome("failed" if n in self.fail_on else "sent")


def test_old_reports_are_not_sent_when_telegram_is_switched_on_later(tmp_path):
    store = InsightStore(tmp_path)
    store.save({**RECORD, "ref_id": "old", "published": "2026-06-01"})
    store.save(RECORD)
    sender = Sender()
    assert send_new(store, sender, ON, lambda r: r["ref_id"], since="2026-08-27") == {"sent": 1, "failed": 0}
    assert sender.sent == ["(1/1)\nr"]


def test_a_partly_sent_message_resumes_at_the_failed_part(tmp_path):
    store = InsightStore(tmp_path)
    store.save(RECORD)
    long_text = "\n".join(f"dòng {i} " + "x" * 300 for i in range(40))  # several Telegram parts
    first = Sender(fail_on={1})
    assert send_new(store, first, ON, lambda r: long_text, since="2026-08-27") == {"sent": 0, "failed": 1}
    assert len(first.sent) == 2 and store.read("acbs", "r")["telegram_parts_sent"] == 1
    second = Sender()
    assert send_new(store, second, ON, lambda r: long_text, since="2026-08-27") == {"sent": 1, "failed": 0}
    assert second.sent[0].startswith("(2/") and len(first.sent) - 1 + len(second.sent) == int(second.sent[0].split("/")[1].split(")")[0])
    assert store.read("acbs", "r")["telegram_sent"] is True


def _client(chunks, delay=0.0):
    def handler(request):
        return httpx.Response(200, content=b"".join(chunks))
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_pdf_download_is_capped_by_size_and_time():
    assert fetch_pdf(_client([b"%PDF-1.4 ", b"x" * 10]), "https://a/x.pdf", max_bytes=100, max_seconds=60) == b"%PDF-1.4 " + b"x" * 10
    with pytest.raises(ValueError, match="too large"):
        fetch_pdf(_client([b"x" * 200]), "https://a/x.pdf", max_bytes=100, max_seconds=60)
    ticks = iter([0, 0, 1000])
    with pytest.raises(TimeoutError):
        fetch_pdf(_client([b"x" * 50]), "https://a/x.pdf", max_bytes=10_000, max_seconds=60, clock=lambda: next(ticks), chunk_size=10)
