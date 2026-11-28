"""Văn bản công bố: the nightly read (docs/superpowers/specs/2026-11-28-van-ban-cong-bo-design.md)."""

import json
from datetime import datetime, timezone

import pytest

from investment_agent.market.filings import FilingStore, doc_id, sync_filings

NOW = datetime(2026, 11, 28, 13, 0, tzinfo=timezone.utc)
SITE = "https://www.example.vn"


def statements_page(*items):
    return "".join(f'<a href="{href}">{label}</a>' for href, label in items)


def vnd_news(*rows):
    return json.dumps({"data": [{"newsTitle": t, "newsDate": d, "newsType": k, "dstockUrl": f"https://dstock.example/{i}",
                                 "attachments": [{"name": "x.pdf", "url": u}]} for i, (t, d, k, u) in enumerate(rows)]})


class Web:
    def __init__(self, pages: dict, files: dict):
        self.pages, self.files, self.fetched = pages, files, []

    def get_text(self, url):
        for prefix, body in self.pages.items():
            if url.startswith(prefix):
                return body
        raise OSError(f"no page {url}")

    def get_bytes(self, url):
        self.fetched.append(url)
        value = self.files[url]
        if isinstance(value, Exception):
            raise value
        return value


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def reader(clock=None, pages=None):
    def read_pdf(data):
        if clock is not None:
            clock.t += 600
        return (pages or [data.decode()]), 1
    return read_pdf


@pytest.fixture
def data(tmp_path):
    (tmp_path / "report-sources.json").write_text(json.dumps({
        "KDH": {"bctc": f"{SITE}/bctc", "cbtt": f"{SITE}/cbtt"}}), encoding="utf-8")
    return tmp_path


def run(data, web, symbols=("KDH",), **kw):
    kw.setdefault("read_pdf", reader())
    return sync_filings(data, list(symbols), get_text=web.get_text, get_bytes=web.get_bytes, now=NOW, sleep=lambda s: None, **kw)


def test_new_statements_are_read_first_up_to_four_a_night(data):
    statements = [(f"{SITE}/2026/{m:02d}/2026{m:02d}29-bctc-hop-nhat.pdf", f"BCTC Hợp nhất ({28 if m == 2 else 29}/{m:02d}/2026)")
                  for m in (4, 7, 10)]
    resolutions = [(f"{SITE}/2026/0{m}/20260{m}10-nq.pdf", f"NQ HĐQT số {m} (10/0{m}/2026)") for m in (5, 6, 8)]
    web = Web({f"{SITE}/bctc": statements_page(*statements), f"{SITE}/cbtt": statements_page(*resolutions),
               "https://api-finfo": vnd_news()},
              {u: b"chu" for u, _ in statements + resolutions})
    out = run(data, web)
    assert web.fetched == [statements[2][0], statements[1][0], statements[0][0], resolutions[2][0]]
    assert len(out["read"]) == 4 and out["pending"] == 2 and out["errors"] == {}
    rec = FilingStore(data / "filings").read("KDH", doc_id(statements[2][0]))
    assert (rec["loai"], rec["ngay"], rec["tieu_de"], rec["trang_nguon"], rec["so_trang"], rec["ocr"], rec["trang"]) == (
        "bctc", "2026-10-29", "BCTC Hợp nhất (29/10/2026)", f"{SITE}/bctc", 1, 1, ["chu"])
    web.fetched.clear()
    assert len(run(data, web)["read"]) == 2  # the next night reads the rest, nothing twice
    assert web.fetched == [resolutions[1][0], resolutions[0][0]]


def test_a_file_seen_on_both_sources_is_read_once(data):
    site = f"{SITE}/2026/08/20260818-kdh-cbtt-nq-hdqt-thong-qua-thanh-lap-cong-ty-con-1.pdf"
    vnd = "https://cdn.example/2026-08-18/20260818%20-%20KDH%20-%20CBTT%20NQ%20HDQT%20thong%20qua%20thanh%20lap%20Cong%20ty%20con%20sign.pdf"
    web = Web({f"{SITE}/bctc": "", f"{SITE}/cbtt": statements_page((site, "NQ HĐQT thông qua thành lập Công ty con (18/08/2026)")),
               "https://api-finfo": vnd_news(("KDH: Nghị quyết HĐQT số 16 ngày 17/08/2026", "2026-08-18", "resolutions", vnd))},
              {site: b"a", vnd: b"a"})
    out = run(data, web)
    assert web.fetched == [site] and len(out["read"]) == 1


def test_vndirect_alone_brings_resolutions_for_a_ticker_without_a_page(data):
    url = "https://cdn.example/2026-06-05/qd.pdf"
    web = Web({"https://api-finfo": vnd_news(("FPT: Quyết định của HĐQT", "2026-06-05", "resolutions", url),
                                             ("FPT: Báo cáo giao dịch cổ phiếu", "2026-06-06", "investor_transaction", "https://cdn.example/gd.pdf"))},
              {url: b"q"})
    out = run(data, web, symbols=("FPT",))
    assert out["read"] == [doc_id(url)] and web.fetched == [url]
    assert FilingStore(data / "filings").read("FPT", doc_id(url))["trang_nguon"] == "https://dstock.example/0"


def test_too_big_files_are_skipped_with_the_reason_and_not_fetched_again(data):
    big, long = f"{SITE}/2026/07/20260729-big.pdf", f"{SITE}/2026/07/20260728-long.pdf"
    web = Web({f"{SITE}/bctc": statements_page((big, "BCTC Hợp nhất (29/07/2026)"), (long, "BCTC Hợp nhất (28/07/2026)")),
               f"{SITE}/cbtt": "", "https://api-finfo": vnd_news()},
              {big: b"x" * (30 * 1024 * 1024 + 1), long: b"y"})
    out = run(data, web, read_pdf=reader(pages=["p"] * 121))
    assert out["skipped"] == {doc_id(big): "tệp quá 30 MB", doc_id(long): "quá 120 trang"} and out["read"] == []
    web.fetched.clear()
    run(data, web)
    assert web.fetched == []


def test_a_failing_file_is_tried_three_nights_then_left(data):
    url = f"{SITE}/2026/07/20260729-loi.pdf"
    web = Web({f"{SITE}/bctc": statements_page((url, "BCTC Hợp nhất (29/07/2026)")), f"{SITE}/cbtt": "",
               "https://api-finfo": vnd_news()}, {url: OSError("timeout")})
    for _ in range(3):
        assert run(data, web)["errors"] == {doc_id(url): "error:OSError"}
    web.fetched.clear()
    assert run(data, web)["errors"] == {} and web.fetched == []


def test_the_time_budget_leaves_the_rest_pending_not_failed(data):
    urls = [f"{SITE}/2026/07/2026072{d}-b.pdf" for d in (1, 2, 3)]
    web = Web({f"{SITE}/bctc": statements_page(*[(u, f"BCTC Hợp nhất (2{i + 1}/07/2026)") for i, u in enumerate(urls)]),
               f"{SITE}/cbtt": "", "https://api-finfo": vnd_news()}, {u: b"c" for u in urls})
    clock = Clock()
    out = run(data, web, read_pdf=reader(clock), clock=clock, budget_seconds=1000)
    assert len(out["read"]) == 2 and out["pending"] == 1 and out["errors"] == {}  # 0 s and 600 s start a file; 1200 s does not


def test_files_before_april_are_left_out(data):
    old, new, undated = f"{SITE}/2026/03/20260330-a.pdf", f"{SITE}/2026/04/20260429-b.pdf", f"{SITE}/tep.pdf"
    web = Web({f"{SITE}/bctc": statements_page((old, "BCTC Hợp nhất (30/03/2026)"), (new, "BCTC Hợp nhất (29/04/2026)"),
                                               (undated, "BCTC Hợp nhất năm 2025")),
               f"{SITE}/cbtt": "", "https://api-finfo": vnd_news()}, {old: b"a", new: b"b", undated: b"c"})
    run(data, web)
    assert web.fetched == [new, undated]


def test_only_the_given_symbols_are_read(data):
    web = Web({f"{SITE}/bctc": statements_page((f"{SITE}/2026/07/20260729-b.pdf", "BCTC Hợp nhất (29/07/2026)")),
               f"{SITE}/cbtt": "", "https://api-finfo": vnd_news()}, {f"{SITE}/2026/07/20260729-b.pdf": b"b"})
    assert run(data, web, symbols=())["read"] == [] and web.fetched == []


def test_a_page_that_fails_is_reported_and_the_other_sources_still_run(data):
    url = "https://cdn.example/2026-06-05/qd.pdf"
    web = Web({f"{SITE}/cbtt": "", "https://api-finfo": vnd_news(("KDH: Quyết định", "2026-06-05", "resolutions", url))}, {url: b"q"})
    out = run(data, web)
    assert out["read"] == [doc_id(url)] and out["page_errors"] == {"KDH bctc": "error:OSError"}
