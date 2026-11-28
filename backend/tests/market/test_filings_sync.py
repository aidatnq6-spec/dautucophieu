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
        if url.endswith("/robots.txt") and url not in self.pages:
            return ""  # no rules: everything allowed
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
    out = run(data, web, max_files=4)
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
    out = run(data, web, read_pdf=reader(clock), clock=clock, budget_seconds=1300, file_seconds=600)
    assert len(out["read"]) == 2 and out["pending"] == 1 and out["errors"] == {}  # 0 s and 600 s start a file; 1200 s has 100 s left


def test_up_to_twenty_files_a_night_within_the_time_budget(data):
    """Owner, 28/11/2026: four a night left 901 filings waiting; short resolutions take about a minute, so the 25 minutes decide."""
    urls = [f"{SITE}/2026/08/202608{d:02d}-nq.pdf" for d in range(1, 26)]
    web = Web({f"{SITE}/bctc": "", f"{SITE}/cbtt": statements_page(*[(u, f"NQ HĐQT ({i + 1:02d}/08/2026)") for i, u in enumerate(urls)]),
               "https://api-finfo": vnd_news()}, {u: b"x" for u in urls})
    out = run(data, web)
    assert len(out["read"]) == 20 and out["pending"] == 5


def test_distinct_numbered_files_and_same_day_resolutions_are_all_kept(data):
    a, b = f"{SITE}/2026/08/20260818-nq-hdqt-so-15.pdf", f"{SITE}/2026/08/20260818-nq-hdqt-so-16.pdf"
    c, d = f"{SITE}/up/nq.pdf", f"{SITE}/up2/nq.pdf"
    web = Web({f"{SITE}/bctc": "", f"{SITE}/cbtt": statements_page(
        (a, "Nghị quyết HĐQT (18/08/2026)"), (b, "Nghị quyết HĐQT (18/08/2026)"), (c, "NQ HĐQT (19/08/2026)"), (d, "NQ HĐQT (20/08/2026)")),
        "https://api-finfo": vnd_news()}, {u: b"x" for u in (a, b, c, d)})
    assert len(run(data, web)["read"]) == 4


def test_a_parent_only_statement_is_dropped_only_when_a_consolidated_one_has_the_same_day(data):
    hn, me, me_alone = (f"{SITE}/2026/07/20260729-hop-nhat.pdf", f"{SITE}/2026/07/20260729-me.pdf", f"{SITE}/2026/04/20260429-me.pdf")
    web = Web({f"{SITE}/bctc": statements_page((hn, "BCTC Hợp nhất Q2.2026 (29/07/2026)"), (me, "BCTC Công ty Mẹ Q2.2026 (29/07/2026)"),
                                               (me_alone, "BCTC Công ty Mẹ Q1.2026 (29/04/2026)")),
               f"{SITE}/cbtt": "", "https://api-finfo": vnd_news()}, {u: b"x" for u in (hn, me, me_alone)})
    run(data, web)
    assert web.fetched == [hn, me_alone]


def test_a_file_killed_mid_read_has_its_attempt_counted(data):
    url = f"{SITE}/2026/07/20260729-b.pdf"
    web = Web({f"{SITE}/bctc": statements_page((url, "BCTC Hợp nhất (29/07/2026)")), f"{SITE}/cbtt": "",
               "https://api-finfo": vnd_news()}, {url: b"x"})

    class Killed(BaseException):
        pass

    def killed(data):
        raise Killed
    with pytest.raises(Killed):
        run(data, web, read_pdf=killed)
    assert FilingStore(data / "filings").state()[doc_id(url)]["attempts"] == 1


def test_pages_ocr_did_not_read_are_kept_with_the_record(data):
    url = f"{SITE}/2026/07/20260729-b.pdf"
    web = Web({f"{SITE}/bctc": statements_page((url, "BCTC Hợp nhất (29/07/2026)")), f"{SITE}/cbtt": "",
               "https://api-finfo": vnd_news()}, {url: b"x"})
    run(data, web, read_pdf=lambda d: (["một", "", "ba"], 2, [2]))
    assert FilingStore(data / "filings").read("KDH", doc_id(url))["trang_chua_doc"] == [2]


def test_robots_disallowed_pages_and_files_are_not_read(data):
    url = f"{SITE}/private/20260729-b.pdf"
    web = Web({f"{SITE}/robots.txt": "User-agent: *\nDisallow: /cbtt\nDisallow: /private/\n",
               f"{SITE}/bctc": statements_page((url, "BCTC Hợp nhất (29/07/2026)")), f"{SITE}/cbtt": statements_page(),
               "https://api-finfo": vnd_news()}, {url: b"x"})
    out = run(data, web)
    assert web.fetched == [] and out["page_errors"]["KDH cbtt"] == "robots.txt không cho đọc"
    assert out["skipped"] == {doc_id(url): "robots.txt không cho đọc"}


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
    assert out["read"] == [doc_id(url)] and out["page_errors"] == {"KDH cafef": "error:OSError", "KDH bctc": "error:OSError"}


CAFEF = "https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx?Symbol="
CDN = "https://cafefnew.mediacdn.vn/Images/Uploaded/DuLieuDownload/BCTC/"


def cafef_list(*rows):
    return json.dumps({"Data": [{"id": i, "Type": 0, "Quarter": int(t[1]), "Year": int(t[3:]), "Time": t, "Name": n, "Link": u}
                                for i, (t, n, u) in enumerate(rows)], "Message": None, "Success": True})


Q3_HN = ("Q3/2026", "Báo cáo tài chính hợp nhất quý 3 năm 2026",
         f"{CDN}KDH_202610302020KDH2020BCTC20Hop20nhat20Q3_30102026153454.pdf?v=1793349295564")
Q3_ME = ("Q3/2026", "Báo cáo tài chính công ty mẹ quý 3 năm 2026",
         f"{CDN}KDH_202610302020KDH2020BCTC20Cong20ty20Me20Q3_30102026153222.pdf?v=1793349144539")


def test_statements_come_from_cafef_and_the_company_page_is_not_read_for_them(data):
    company = (f"{SITE}/2026/10/20261029-bctc-hop-nhat.pdf", "BCTC Hợp nhất (29/10/2026)")
    web = Web({CAFEF + "KDH": cafef_list(Q3_HN), f"{SITE}/bctc": statements_page(company), f"{SITE}/cbtt": "",
               "https://api-finfo": vnd_news()},
              {Q3_HN[2].split("?")[0]: b"chu"})
    out = run(data, web)
    assert web.fetched == [Q3_HN[2].split("?")[0]] and "page_errors" not in out
    rec = FilingStore(data / "filings").records("KDH")[0]
    assert rec["loai"] == "bctc" and rec["ngay"] == "2026-10-30" and rec["tieu_de"] == Q3_HN[1]
    assert rec["nguon"] == Q3_HN[2].split("?")[0] and rec["trang_nguon"] == CAFEF + "KDH&Type=1&Year=0"


def test_a_cafef_parent_only_statement_is_dropped_when_the_same_period_has_a_consolidated_one(data):
    q2_me = ("Q2/2026", "Báo cáo tài chính công ty mẹ quý 2 năm 2026", f"{CDN}KDH_20260731_Me_Q2.pdf")
    web = Web({CAFEF + "KDH": cafef_list(Q3_HN, Q3_ME, q2_me), f"{SITE}/bctc": "", f"{SITE}/cbtt": "",
               "https://api-finfo": vnd_news()},
              {u.split("?")[0]: b"chu" for _, _, u in (Q3_HN, Q3_ME, q2_me)})
    run(data, web)
    assert web.fetched == [Q3_HN[2].split("?")[0], q2_me[2]]


def test_cafef_files_without_a_date_keep_only_this_years_and_older_ones_are_left_out(data):
    old = ("Q2/2025", "Báo cáo tài chính hợp nhất quý 2 năm 2025", f"{CDN}KDH_20250730_HN_Q2.pdf")
    undated_now = ("Q1/2026", "Báo cáo tài chính hợp nhất quý 1 năm 2026", f"{CDN}CTC_Hop_nhat_Q1.2026_1777447818.pdf")
    undated_old = ("Q4/2025", "Báo cáo tài chính hợp nhất quý 4 năm 2025", f"{CDN}CTC_Hop_nhat_Q4.2025_1769000000.pdf")
    web = Web({CAFEF + "KDH": cafef_list(old, undated_now, undated_old), f"{SITE}/bctc": "", f"{SITE}/cbtt": "",
               "https://api-finfo": vnd_news()},
              {u: b"chu" for _, _, u in (old, undated_now, undated_old)})
    run(data, web)
    assert web.fetched == [undated_now[2]]
    assert FilingStore(data / "filings").records("KDH")[0]["ngay"] is None


def test_the_company_statements_page_is_used_when_cafef_has_none_or_fails(data):
    company = (f"{SITE}/2026/10/20261029-bctc-hop-nhat.pdf", "BCTC Hợp nhất (29/10/2026)")
    for cafef, error in ((cafef_list(), False), (None, True)):
        pages = {f"{SITE}/bctc": statements_page(company), f"{SITE}/cbtt": "", "https://api-finfo": vnd_news()}
        if cafef is not None:
            pages[CAFEF + "KDH"] = cafef
        web = Web(pages, {company[0]: b"chu"})
        d = data / ("loi" if error else "rong")
        d.mkdir()
        (d / "report-sources.json").write_text((data / "report-sources.json").read_text(encoding="utf-8"), encoding="utf-8")
        out = run(d, web)
        assert web.fetched == [company[0]]
        assert ("KDH cafef" in out.get("page_errors", {})) is error


def test_a_watched_ticker_without_any_company_page_still_gets_cafef_statements(data):
    web = Web({CAFEF + "VCB": cafef_list(("Q3/2026", "Báo cáo tài chính hợp nhất quý 3 năm 2026", f"{CDN}VCB_20261030_HN.pdf")),
               "https://api-finfo": vnd_news()},
              {f"{CDN}VCB_20261030_HN.pdf": b"chu"})
    out = run(data, web, symbols=("VCB",))
    assert out["read"] and web.fetched == [f"{CDN}VCB_20261030_HN.pdf"]


class Page(str):
    url: str


def test_links_on_a_redirected_page_resolve_against_where_it_landed(data):
    page = Page(statements_page(("20261029-bctc-hop-nhat.pdf", "BCTC Hợp nhất (29/10/2026)")))
    page.url = f"{SITE}/vi/co-dong/2026/"
    landed = f"{SITE}/vi/co-dong/2026/20261029-bctc-hop-nhat.pdf"
    web = Web({f"{SITE}/bctc": page, f"{SITE}/cbtt": "", "https://api-finfo": vnd_news()}, {landed: b"chu"})
    out = run(data, web)
    assert web.fetched == [landed] and out["read"] == [doc_id(landed)]
