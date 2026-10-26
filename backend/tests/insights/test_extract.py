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
    assert out["macro_now"] == {"view": None, "reasons": []} and out["macro_outlook"]["reasons"] == [] and out["sectors"] == []


def test_normalise_ignores_case_spacing_and_punctuation():
    assert normalise("  Lãi suất   THẤP, hỗ-trợ ") == normalise("lãi suất thấp hỗ trợ")


def test_validate_survives_non_string_fields():
    raw = {"macro_now": {"view": ["favourable"], "reasons": [{"text": "x", "quote": {"q": 1}, "page": 1}]},
           "sectors": [{"sector": ["Ngân hàng"], "effect": "benefit", "reason": "x", "quote": "lãi suất thấp hỗ trợ ngành ngân hàng", "page": 2},
                       {"sector": "Ngân hàng", "effect": {"x": 1}, "reason": "x", "quote": "lãi suất thấp hỗ trợ ngành ngân hàng", "page": 2}]}
    out = validate(raw, PAGES, SECTORS)
    assert out["sectors"] == [] and out["macro_now"]["reasons"] == [] and out["dropped"] == 3


def test_short_or_partial_word_quotes_do_not_count_as_evidence():
    # Whitespace is ignored when matching (pypdf splits syllables), so word boundaries cannot be checked; a quote must
    # instead be long enough (6 words, 25 characters) that it can only come from the report itself.
    cases = [("ng", 2), ("ngân hàng", 2), ("7,5%", 1), ("ăng trưởng GDP", 1)]
    for quote, page in cases:
        raw = {"sectors": [{"sector": "Ngân hàng", "effect": "benefit", "reason": "x", "quote": quote, "page": page}],
               "macro_now": {"view": "favourable", "reasons": [{"text": "x", "quote": quote, "page": page}]}}
        out = validate(raw, PAGES, SECTORS)
        assert out["sectors"] == [] and out["macro_now"]["reasons"] == [], quote


def test_macro_view_without_any_verified_reason_is_not_kept():
    raw = {"macro_now": {"view": "favourable", "reasons": [{"text": "bịa", "quote": "Lạm phát vượt mười phần trăm năm nay", "page": 1}]},
           "macro_outlook": {"view": "unfavourable", "reasons": []}, "sectors": []}
    out = validate(raw, PAGES, SECTORS)
    assert out["macro_now"] == {"view": None, "reasons": []} and out["macro_outlook"]["view"] is None


def test_quotes_match_pdf_text_with_syllables_split_by_spaces_and_newlines():
    """26/10/2026: pypdf splits Vietnamese syllables ("T\n ổng  \nm\nức"); verbatim quotes were all dropped."""
    broken = ["T\n ổng  \nm\nức bán l\nẻ hàng hóa và doanh thu d\nịch v\nụ tiêu dùng tăng 14,12% so v\nới cùng k\nỳ"]
    raw = {"macro_now": {"view": "favourable", "reasons": [
        {"text": "Bán lẻ tăng", "quote": "Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng tăng 14,12%", "page": 1}]},
        "macro_outlook": {"view": "neutral", "reasons": []}, "sectors": []}
    out = validate(raw, broken, SECTORS)
    assert len(out["macro_now"]["reasons"]) == 1 and out["macro_now"]["view"] == "favourable"


def test_quotes_still_need_enough_words_to_be_evidence():
    raw = {"macro_now": {"view": "favourable", "reasons": [{"text": "x", "quote": "Tăng trưởng GDP quý III", "page": 1}]},
           "macro_outlook": {"view": "neutral", "reasons": []}, "sectors": []}
    assert validate(raw, PAGES, SECTORS)["macro_now"]["reasons"] == []  # 5 words: too short to count
