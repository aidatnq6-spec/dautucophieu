from datetime import datetime
from zoneinfo import ZoneInfo

from investment_agent.brief.news import parse_rss, pick_news, window_items

VN = ZoneInfo("Asia/Ho_Chi_Minh")
RSS = """<rss><channel>
<item><title><![CDATA[Phiên 26/10: Khối ngoại bán ròng gần 900 tỷ, xả mạnh HPG]]></title><link>https://cafef.vn/a.chn</link>
<pubDate>Mon, 26 Oct 26 16:07:13 +0700</pubDate></item>
<item><title>NHNN giữ nguyên lãi suất điều hành &amp; tỷ giá</title><link>https://cafef.vn/b.chn</link><pubDate>Mon, 26 Oct 2026 09:00:00 +0700</pubDate></item>
<item><title>Tin xấu</title><link>javascript:alert(1)</link><pubDate>Mon, 26 Oct 2026 10:00:00 +0700</pubDate></item>
</channel></rss>"""


def test_rss_items_are_parsed_with_time_and_unsafe_links_dropped():
    items = parse_rss(RSS, "CafeF")
    assert [i["title"] for i in items] == ["Phiên 26/10: Khối ngoại bán ròng gần 900 tỷ, xả mạnh HPG", "NHNN giữ nguyên lãi suất điều hành & tỷ giá"]
    assert items[0]["published"] == "2026-10-26T16:07:13+07:00" and items[0]["source"] == "CafeF"


def test_window_keeps_recent_unique_titles_newest_first():
    a = parse_rss(RSS, "CafeF")
    b = [{**a[0], "source": "Vietstock", "url": "https://vietstock.vn/x.htm", "title": "Phiên 26/10:  khối ngoại bán ròng gần 900 tỷ, xả mạnh HPG!"}]
    old = [{"title": "Cũ", "url": "https://x.vn/c", "source": "Vneconomy", "published": "2026-10-22T10:00:00+07:00"}]
    out = window_items(a + b + old, since=datetime(2026, 10, 23, 15, tzinfo=VN), until=datetime(2026, 10, 26, 17, tzinfo=VN))
    assert [i["url"] for i in out] == ["https://cafef.vn/a.chn", "https://cafef.vn/b.chn"]


def item(title, minute=0):
    return {"title": title, "url": f"https://x.vn/{abs(hash(title))}", "source": "CafeF", "published": f"2026-10-26T10:{minute:02d}:00+07:00"}


def test_held_outranks_watched_outranks_sector_and_macro():
    items = [item("Fed giữ lãi suất", 1), item("FPT ký hợp đồng lớn", 2), item("Ngân hàng đua giảm lãi vay", 3),
             item("HPG lãi quý III tăng", 4), item("Bóng đá cuối tuần", 5), item("MBBank mở chi nhánh", 6)]
    out = pick_news(items, watched=["FPT", "MBB"], held={"HPG"}, sector_names={"Ngân hàng"}, limit=4)
    assert [i["title"] for i in out] == ["HPG lãi quý III tăng", "FPT ký hợp đồng lớn", "Ngân hàng đua giảm lãi vay", "Fed giữ lãi suất"]
    assert out[0]["reason"] == "HPG" and out[3]["reason"] == "vĩ mô"
    # "MBB" is a whole-word match only: "MBBank" does not count as MBB.
    assert all("MBBank" not in i["title"] for i in pick_news(items, watched=["MBB"], held=set(), sector_names=set(), limit=10))
