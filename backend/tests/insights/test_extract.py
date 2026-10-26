import json

from investment_agent.insights.extract import RESPONSE_FORMAT, build_messages, normalise, validate

SECTORS = ["Ngân hàng", "Bất động sản", "Dầu khí"]
PAGES = ["Tăng trưởng GDP quý III đạt 7,5%, cao hơn kỳ vọng.",
         "Lãi suất thấp hỗ trợ ngành ngân hàng; giá dầu giảm gây áp lực lên doanh nghiệp dầu khí."]


def test_messages_carry_only_report_text_sectors_and_instructions():
    msgs = build_messages("Cập nhật vĩ mô tháng 10/2026", PAGES, SECTORS)
    blob = json.dumps(msgs, ensure_ascii=False)
    assert "[Trang 1]" in blob and "[Trang 2]" in blob and "Ngân hàng" in blob
    for private in ("MBB", "SSI", "HPG", "KDH", "watchlist", "danh mục của", "đang nắm", "giá vốn"):
        assert private not in blob
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert RESPONSE_FORMAT["type"] == "json_schema"


def test_long_reports_are_cut_at_a_page_boundary():
    msgs = build_messages("t", ["x" * 70_000, "y" * 70_000], SECTORS)
    assert "[Trang 1]" in msgs[1]["content"] and "[Trang 2]" not in msgs[1]["content"]


def test_validate_keeps_quoted_claims_and_drops_invented_or_unknown_ones():
    raw = {"macro_now": {"view": "favourable", "reasons": [
               {"text": "GDP tăng mạnh", "quote": "Tăng trưởng GDP quý III đạt 7,5%", "page": 1},
               {"text": "bịa", "quote": "Lạm phát vượt 10%", "page": 1}]},
           "macro_outlook": {"view": "neutral", "reasons": []},
           "sectors": [{"sector": "Ngân hàng", "effect": "benefit", "reason": "lãi suất thấp",
                        "quote": "lãi suất thấp hỗ trợ ngành ngân hàng", "page": 2},
                       {"sector": "Hàng không", "effect": "harm", "reason": "x", "quote": "giá dầu giảm", "page": 2},
                       {"sector": "Dầu khí", "effect": "harm", "reason": "giá dầu giảm", "quote": "giá dầu giảm gây áp lực", "page": 1}]}
    out = validate(raw, PAGES, SECTORS)
    assert [r["text"] for r in out["macro_now"]["reasons"]] == ["GDP tăng mạnh"]
    assert [(s["sector"], s["effect"]) for s in out["sectors"]] == [("Ngân hàng", "benefit")]  # unknown sector and wrong page dropped
    assert out["dropped"] == 3


def test_validate_survives_malformed_model_output():
    out = validate({"macro_now": {"view": "great", "reasons": [{"text": "x", "quote": "Tăng trưởng GDP", "page": "one"}]},
                    "sectors": "none"}, PAGES, SECTORS)
    assert out["macro_now"] == {"view": "neutral", "reasons": []} and out["macro_outlook"]["reasons"] == [] and out["sectors"] == []


def test_normalise_ignores_case_spacing_and_punctuation():
    assert normalise("  Lãi suất   THẤP, hỗ-trợ ") == normalise("lãi suất thấp hỗ trợ")
