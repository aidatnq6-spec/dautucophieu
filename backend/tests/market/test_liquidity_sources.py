import json
from datetime import date

import pytest

from investment_agent.market.leading import MacroError, evaluate, parse_nso_report, parse_sbv_central
from investment_agent.market.omo import OmoStore, parse_omo

# Synthetic pages in the shape of sbv.gov.vn and nso.gov.vn (11/2026); every figure is made up.
CENTRAL = """<div><h3>Tỷ giá trung tâm</h3><p>Ngân hàng Nhà nước Việt Nam công bố tỷ giá trung tâm của Đồng Việt Nam với Đô la Mỹ,
 áp dụng cho ngày 14/11/2026 như sau:</p><table><tr><td>Tỷ giá</td><td>1 Đô la Mỹ = </td><td>25.100 VND</td></tr></table>
 <p>Số văn bản 1/TB-NHNN</p></div>"""

OMO = """<h4 class="ls01-subheading">KẾT QUẢ ĐẤU THẦU THỊ TRƯỜNG MỞ</h4> <div class="ls01-date"> Ngày 13 tháng 11 năm 2026 </div>
<table class="ls01-table"><thead><tr><th>Loại hình giao dịch</th><th>Số thành viên</th><th>Khối lượng</th><th>Lãi suất</th></tr></thead><tbody>
<tr class="ls01-group"><td colspan="4">Mua kỳ hạn</td></tr>
<tr><td class="text-left">- Kỳ hạn 7 ngày</td><td>5/5</td><td>1.000,50</td><td>4,5</td></tr>
<tr><td class="text-left">- Kỳ hạn 91 ngày</td><td>0/0</td><td>,00</td><td>0</td></tr>
<tr class="ls01-group"><td colspan="4">Bán hẳn</td></tr>
<tr><td class="text-left">- Kỳ hạn 14 ngày</td><td>2/2</td><td>300</td><td>4,0</td></tr>
<tr class="ls01-total"><td><em>Tổng cộng</em></td><td></td><td>1.300,50</td><td></td></tr></tbody></table>"""


def report(title, body, day="2026-11-03T09:00:00"):
    return {"date": day, "title": {"rendered": title}, "content": {"rendered": f"<p>{body}</p>"}}


REPORTS = json.dumps([
    report("Báo cáo tình hình kinh tế &#8211; xã hội tháng Mười và 10 tháng năm 2026",
           "cán cân thương mại hàng hóa tháng Mười xuất siêu 2,50 tỷ USD, sau khi xuất siêu 1,00 tỷ USD trong tháng Chín. Tính chung mười tháng"
           " năm 2026, kim ngạch tăng. Do nhập khẩu tăng nhanh hơn xuất khẩu, cán cân thương mại hàng hóa nhập siêu 1.012,07 tỷ USD. "
           "Vốn đầu tư trực tiếp nước ngoài thực hiện tại Việt Nam mười tháng năm 2026 ước đạt 20,50 tỷ USD, tăng 10,1% so với cùng kỳ năm trước."),
    report("Thông cáo báo chí tình hình kinh tế – xã hội quý III và 9 tháng năm 2026", "cán cân thương mại hàng hóa tháng Chín xuất siêu 9 tỷ USD"),
    report("Báo cáo tình hình kinh tế – xã hội Quý II và sáu tháng đầu năm 2026",
           "cán cân thương mại hàng hóa tháng Sáu ước tính nhập siêu 0,40 tỷ USD. Tính chung 6 tháng, cán cân thương mại hàng hóa ước tính xuất siêu "
           "3,2 tỷ USD. Vốn đầu tư trực tiếp nước ngoài thực hiện tại Việt Nam 6 tháng đầu năm 2026 ước đạt 11 tỷ USD, giảm 2,0% so với cùng kỳ.",
           day="2026-07-03T09:00:00"),
])


def test_the_central_rate_is_dated_on_the_day_it_applies_to():
    assert parse_sbv_central(CENTRAL) == [(date(2026, 11, 14), "25100")]
    with pytest.raises(MacroError):
        parse_sbv_central("<p>Tỷ giá trung tâm</p>")


def test_monthly_reports_give_the_trade_balance_and_disbursed_fdi_at_the_month_end():
    assert parse_nso_report(REPORTS, field="trade_month") == [(date(2026, 6, 30), "-0.4"), (date(2026, 10, 31), "2.5")]
    assert parse_nso_report(REPORTS, field="trade_ytd") == [(date(2026, 6, 30), "3.2"), (date(2026, 10, 31), "-1012.07")]
    assert parse_nso_report(REPORTS, field="fdi_ytd") == [(date(2026, 6, 30), "11"), (date(2026, 10, 31), "20.5")]
    assert parse_nso_report(REPORTS, field="fdi_yoy") == [(date(2026, 6, 30), "-2"), (date(2026, 10, 31), "10.1")]
    with pytest.raises(MacroError):
        parse_nso_report(json.dumps([report("Báo cáo tình hình kinh tế – xã hội tháng Mười năm 2026", "không có số")]), field="trade_month")


RETAIL = json.dumps([
    report("Báo cáo tình hình kinh tế – xã hội tháng Mười và 10 tháng năm 2026",
           "Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng Mười ước đạt 600,5 nghìn tỷ đồng, tăng 1,0% so với tháng "
           "trước và tăng 13,7% so với cùng kỳ năm trước. Tính chung mười tháng, tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện "
           "hành ước đạt 6.000 nghìn tỷ đồng. Vốn đầu tư thực hiện từ nguồn ngân sách nhà nước tháng Mười đạt 100,6 nghìn tỷ đồng, tăng 20,7% so với "
           "cùng kỳ năm trước. Tính chung mười tháng, vốn đầu tư thực hiện từ nguồn ngân sách nhà nước ước đạt 700,9 nghìn tỷ đồng, bằng 60,0% kế "
           "hoạch năm và tăng 18,8% so với cùng kỳ năm trước (cùng kỳ năm 2025 bằng 64,3% và tăng 30,7%)."),
    # quarter reports give total social investment instead: no budget figure that month
    report("Báo cáo tình hình kinh tế – xã hội quý III và 9 tháng năm 2026",
           "Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng Chín năm 2026 ước đạt gần 590 nghìn tỷ đồng, giảm 0,5% "
           "so với cùng kỳ năm trước."),
    report("Báo cáo tình hình kinh tế – xã hội tháng 01 năm 2026",
           "Vốn đầu tư thực hiện từ nguồn ngân sách Nhà nước tháng 01/2026 ước đạt 43,1 nghìn tỷ đồng, bằng 4,8% kế hoạch năm và tăng 9,3% so với "
           "cùng kỳ năm trước (cùng kỳ năm 2025 bằng 3,6% và tăng 11,8%)."),
])


def test_monthly_reports_give_retail_sales_and_budget_investment_growth():
    assert parse_nso_report(RETAIL, field="retail_yoy") == [(date(2026, 9, 30), "-0.5"), (date(2026, 10, 31), "13.7")]
    # since January (January's own sentence is the year to date), not the month alone
    assert parse_nso_report(RETAIL, field="public_invest_yoy") == [(date(2026, 1, 31), "9.3"), (date(2026, 10, 31), "18.8")]


def test_reports_typed_with_separate_accents_read_the_same():
    import unicodedata
    decomposed = unicodedata.normalize("NFD", json.loads(RETAIL)[0]["content"]["rendered"])  # "tháng", "đạt" as some reports type them
    post = {**json.loads(RETAIL)[0], "content": {"rendered": decomposed}}
    assert parse_nso_report(json.dumps([post]), field="retail_yoy") == [(date(2026, 10, 31), "13.7")]


def test_a_rule_of_none_gives_the_trend_only():
    assert evaluate("none", ["1", "2"]) == ("Tăng", None)


def test_the_omo_page_gives_each_session_by_kind_and_tenor(tmp_path):
    s = parse_omo(OMO)
    assert s["date"] == "2026-11-13" and s["total"] == "1300.5"
    assert s["rows"] == [{"kind": "repo", "group": "Mua kỳ hạn", "term_days": 7, "members": "5/5", "volume": "1000.5", "rate": "4.5"},
                         {"kind": "repo", "group": "Mua kỳ hạn", "term_days": 91, "members": "0/0", "volume": "0", "rate": "0"},
                         {"kind": "bill", "group": "Bán hẳn", "term_days": 14, "members": "2/2", "volume": "300", "rate": "4"}]
    store = OmoStore(tmp_path)
    store.upsert(s)
    store.upsert({**s, "total": "1"})  # the same day again: replaced, not added
    assert [x["total"] for x in store.sessions()] == ["1"]
    with pytest.raises(MacroError):
        parse_omo("<p>Kết quả đấu thầu</p>")
