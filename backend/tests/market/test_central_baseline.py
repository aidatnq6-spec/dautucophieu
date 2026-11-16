from datetime import date

from investment_agent.market.leading import MacroStore, fetch_central_baseline, parse_ttt_central, parse_ttt_sitemap

# In the shape of thitruongtaichinhtiente.vn (11/2026): a daily sitemap and a daily central-rate article; the figure is made up.
SITEMAP = """<urlset><url><loc>https://thitruongtaichinhtiente.vn/gdp-nam-2025-tang-75909.html</loc></url>
<url><loc>https://thitruongtaichinhtiente.vn/ngay-6-1-ty-gia-trung-tam-giam-2-dong-75924.html</loc></url></urlset>"""
ARTICLE = ('<script type="application/ld+json">{"datePublished": "2026-01-06T09:56:01+07:00"}</script><p>Sáng ngày 6/1, tỷ giá trung tâm giữa đồng Việt Nam '
           '(VND) với đồng đô la Mỹ (USD) được Ngân hàng Nhà nước Việt Nam (NHNN) công bố ở mức 25.100 đồng, giảm 2 đồng so với chốt phiên ngày 5/1. '
           'Với biên độ ±5%, tỷ giá trần hôm nay là 26.355 VND/USD.</p><p>Bài liên quan: Ngày 16/11, Ngân hàng Nhà nước công bố tỷ giá trung tâm ở mức 25.637.</p>')


def test_the_sitemap_gives_the_days_central_rate_articles_and_the_article_its_first_rate():
    assert parse_ttt_sitemap(SITEMAP) == ["https://thitruongtaichinhtiente.vn/ngay-6-1-ty-gia-trung-tam-giam-2-dong-75924.html"]
    assert parse_ttt_central(ARTICLE) == (date(2026, 1, 6), "25100")  # the day's own rate, not a related article's
    assert parse_ttt_central("<p>Tỷ giá hôm nay</p>") is None


def test_the_start_of_year_rate_is_looked_up_once_a_year_until_found(tmp_path):
    store, asked = MacroStore(tmp_path), []

    def get(url):
        asked.append(url)
        if "sitemap-article-2026-01-06" in url:
            return SITEMAP
        if url.endswith("75924.html"):
            return ARTICLE
        return "<urlset></urlset>"
    assert fetch_central_baseline(store, tmp_path, get=get, today=date(2026, 11, 16)) == "ok"
    obs = store.read("usd_vnd_central")
    assert [(o["date"], o["value"], o["entry"]) for o in obs] == [("2026-01-06", "25100", "auto")] and "75924" in obs[0]["source_url"]
    assert [u.rsplit("-", 3)[-3:] for u in asked if "sitemap" in u][-1] == ["2026", "01", "06.xml"]  # stops at the first found
    asked.clear()
    assert fetch_central_baseline(store, tmp_path, get=get, today=date(2026, 11, 17)) == "ok" and asked == []  # stored: nothing asked


def test_a_year_without_an_article_in_its_first_week_is_not_searched_again(tmp_path):
    store, asked = MacroStore(tmp_path), []
    get = lambda url: asked.append(url) or "<urlset></urlset>"  # noqa: E731
    assert fetch_central_baseline(store, tmp_path, get=get, today=date(2026, 11, 16)) == "not_found" and len(asked) == 7
    asked.clear()
    assert fetch_central_baseline(store, tmp_path, get=get, today=date(2026, 11, 17)) == "not_found" and asked == []
    assert fetch_central_baseline(store, tmp_path, get=get, today=date(2027, 1, 3)) == "waiting" and asked == []  # first week not over
