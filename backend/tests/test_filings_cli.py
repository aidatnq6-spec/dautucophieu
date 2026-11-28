"""Văn bản công bố: the filings-sync and filings-check commands."""

import json

from investment_agent.cli import filings_check, filings_sync, main

PAGE = ('<a href="/up/2026/07/20260729-bctc-hop-nhat.pdf">BCTC Hợp nhất Q2.2026 (29/07/2026)</a>'
        '<a href="/up/2026/07/20260729-bctc-me.pdf">BCTC Công ty Mẹ Q2.2026 (29/07/2026)</a>'
        '<a href="/up/2026/06/20260605-qd.pdf">Quyết định về việc chuyển nhượng phần vốn góp (05/06/2026)</a>')


def web(robots="User-agent: *\nDisallow: /wp-admin/\n"):
    def get_text(url):
        if url.endswith("/robots.txt"):
            return robots
        if url.startswith("https://www.example.vn/co-dong"):
            return PAGE
        if url.startswith("https://api-finfo"):
            return json.dumps({"data": []})
        raise OSError(url)
    return get_text


def test_filings_sync_prints_what_it_read_and_exits_1_on_errors(tmp_path, capsys):
    (tmp_path / "market-symbols.txt").write_text("KDH\n", encoding="utf-8")
    (tmp_path / "report-sources.json").write_text(json.dumps({"KDH": {"bctc": "https://www.example.vn/co-dong/bctc"}}), encoding="utf-8")
    files = {"https://www.example.vn/up/2026/07/20260729-bctc-hop-nhat.pdf": b"a"}

    def get_bytes(url):
        if url in files:
            return files[url]
        raise OSError(url)
    code = filings_sync(tmp_path, get_text=web(), get_bytes=get_bytes, read_pdf=lambda data: (["trang"], 0), sleep=lambda s: None)
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["status"] == "partial" and len(out["read"]) == 1 and len(out["errors"]) == 1  # the decision's file fails
    assert (tmp_path / "filings" / "KDH").is_dir()


def test_filings_check_lists_readable_links_and_robots(capsys):
    assert filings_check("https://www.example.vn/co-dong/bctc", get_text=web()) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["robots"] == "allow"
    assert out["bctc"] == [{"nhan": "BCTC Hợp nhất Q2.2026 (29/07/2026)", "ngay": "2026-07-29",
                            "url": "https://www.example.vn/up/2026/07/20260729-bctc-hop-nhat.pdf"}]
    assert [x["ngay"] for x in out["nghi_quyet"]] == ["2026-06-05"]
    assert filings_check("https://www.example.vn/co-dong/bctc", get_text=web("User-agent: *\nDisallow: /co-dong/\n")) == 1
    assert json.loads(capsys.readouterr().out)["robots"] == "disallow"

    def robots_fails(url):
        if url.endswith("/robots.txt"):
            raise OSError("403")
        return web()(url)
    assert filings_check("https://www.example.vn/co-dong/bctc", get_text=robots_fails) == 1  # unreadable robots.txt: not read
    assert json.loads(capsys.readouterr().out)["robots"] == "disallow"


def test_the_commands_are_registered(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr("investment_agent.cli.filings_sync", lambda data_dir, **kw: seen.setdefault("sync", data_dir) and 0)
    monkeypatch.setattr("investment_agent.cli.filings_check", lambda url, **kw: seen.setdefault("check", url) and 0)
    monkeypatch.setattr("sys.argv", ["cli", "filings-sync", "--data-dir", str(tmp_path)])
    assert main() == 0
    monkeypatch.setattr("sys.argv", ["cli", "filings-check", "--url", "https://www.example.vn/co-dong/bctc"])
    assert main() == 0
    assert seen == {"sync": tmp_path, "check": "https://www.example.vn/co-dong/bctc"}


def test_a_file_over_30_mb_stops_downloading_once_it_passes_the_limit():
    import httpx

    from investment_agent.cli import _filings_get_bytes
    from investment_agent.market.filings import MAX_BYTES
    sent = []

    def chunks():
        for _ in range(64):  # 64 MB offered
            sent.append(1)
            yield b"x" * (1024 * 1024)

    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=chunks())))
    data = _filings_get_bytes("https://cdn.example/big.pdf", client=client)
    assert len(data) > MAX_BYTES and len(sent) <= 32


def test_a_small_file_is_downloaded_whole():
    import httpx

    from investment_agent.cli import _filings_get_bytes
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"%PDF-1.7 nho")))
    assert _filings_get_bytes("https://cdn.example/a.pdf", client=client) == b"%PDF-1.7 nho"


def test_a_page_keeps_the_address_it_was_redirected_to():
    import httpx

    from investment_agent.cli import _filings_get_text

    def handler(request):
        if request.url.path == "/co-dong":
            return httpx.Response(301, headers={"Location": "https://www.example.vn/vi/co-dong/bctc/"})
        return httpx.Response(200, text="<a href='a.pdf'>x</a>")
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    page = _filings_get_text("https://www.example.vn/co-dong", client=client)
    assert page == "<a href='a.pdf'>x</a>" and page.url == "https://www.example.vn/vi/co-dong/bctc/"


def test_filings_check_resolves_links_where_a_redirected_page_landed(capsys):
    from investment_agent.cli import _Page

    def get_text(url):
        if url.endswith("/robots.txt"):
            return ""
        page = _Page('<a href="20261030-bctc-hop-nhat.pdf">BCTC Hợp nhất Q3.2026 (30/10/2026)</a>')
        page.url = "https://www.example.vn/vi/co-dong/2026/"
        return page
    assert filings_check("https://www.example.vn/co-dong", get_text=get_text) == 0
    assert "https://www.example.vn/vi/co-dong/2026/20261030-bctc-hop-nhat.pdf" in capsys.readouterr().out
