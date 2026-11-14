import json
from datetime import datetime, timezone

from investment_agent.market.gold_price import GoldPriceStore, gold_price_sync, gold_prices

NOW = datetime(2026, 11, 6, 14, 0, tzinfo=timezone.utc)


def page(rows, *, unit="(VNĐ/Chỉ)", when="18:28 06/11/2026"):
    body = "".join(f'<tr><td class="text-center">{name}</td>' + f'<td class="buy-price">{buy}</td>'
                   + (f'<td class="sell-price">{sell}</td>' if sell is not None else "") + "</tr>" for name, buy, sell in rows)
    return (f'<html><body><p class="update-time">Giá vàng cập nhật lần cuối lúc {when}</p><div id="priceList"><table><thead><tr>'
            f'<th>Loại vàng</th><th><p>Mua vào</p><p>{unit}</p></th><th><p>Bán ra</p><p>{unit}</p></th></tr></thead>'
            f'<tbody>{body}</tbody></table></div></body></html>')


ROWS = [("Vàng miếng SJC", "13,750,000", "14,100,000"), ("Nhẫn tròn Phú Quý 999.9", "13,750,000", "14,050,000"),
        ("Vàng 999.9 phi SJC", "12,900,000", None), ("Bạc thỏi Phú Quý 999 (1Kilo, 10 lượng)", "157,100", "162,000")]


def test_one_page_stores_every_gold_kind_per_chi_with_the_time_it_gives_and_leaves_silver_out(tmp_path):
    asked = []
    out = gold_price_sync(GoldPriceStore(tmp_path), get=lambda url: asked.append(url) or page(ROWS), now=NOW)
    assert out == {"status": "ok", "kinds": 3} and asked == ["https://phuquygroup.vn/"]
    g = gold_prices(tmp_path)
    assert g["source"] == "Phú Quý" and g["unit"] == "chỉ" and g["as_of"] == "2026-11-06T18:28:00+07:00"
    assert g["kinds"] == {"Vàng miếng SJC": {"buy": "13750000", "sell": "14100000"}, "Nhẫn tròn Phú Quý 999.9": {"buy": "13750000", "sell": "14050000"},
                          "Vàng 999.9 phi SJC": {"buy": "12900000", "sell": None}}


def test_a_changed_unit_a_failed_or_empty_page_keeps_what_was_stored(tmp_path):
    store = GoldPriceStore(tmp_path)
    gold_price_sync(store, get=lambda u: page(ROWS[:1]), now=NOW)
    assert gold_price_sync(store, get=lambda u: page(ROWS, unit="(VNĐ/Lượng)"), now=NOW) == {"status": "error", "reason": "unit"}
    assert gold_price_sync(store, get=lambda u: page([]), now=NOW)["status"] == "error"
    assert gold_price_sync(store, get=lambda u: "<html></html>", now=NOW)["status"] == "error"

    def boom(u):
        raise OSError("down")
    assert gold_price_sync(store, get=boom, now=NOW)["status"] == "error"
    assert list(gold_prices(tmp_path)["kinds"]) == ["Vàng miếng SJC"]
    assert gold_prices(None) == {} and gold_prices(tmp_path / "none") == {}


def test_each_day_s_buying_price_of_every_kind_is_kept(tmp_path):
    from investment_agent.market.gold_price import gold_history
    store = GoldPriceStore(tmp_path)
    gold_price_sync(store, get=lambda url: page(ROWS), now=NOW)
    gold_price_sync(store, get=lambda url: page([("Vàng miếng SJC", "13,800,000", "14,150,000")], when="09:00 07/11/2026"), now=NOW)
    gold_price_sync(store, get=lambda url: page([("Vàng miếng SJC", "13,900,000", "14,200,000")], when="15:00 07/11/2026"), now=NOW)  # later the same day
    assert gold_history(tmp_path)["Vàng miếng SJC"] == {"2026-11-06": "13750000", "2026-11-07": "13900000"}
    assert gold_history(tmp_path)["Nhẫn tròn Phú Quý 999.9"] == {"2026-11-06": "13750000"}
