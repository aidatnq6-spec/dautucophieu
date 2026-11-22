"""Thống kê lịch sử (owner, 21/11/2026): VN-Index H sessions later, grouped by a state known on the day: P/E against its own five
years, and the macro lights' levels. Every group says its samples and how many of them do not overlap (days at least H sessions
apart), and its t-statistic stands on those alone: overlapping windows are not independent."""

from datetime import date, timedelta
from decimal import Decimal

from investment_agent.domain.history_stats import forward_returns, group_summary, independent, pe_groups

D = Decimal


def sessions(values, start=date(2018, 1, 1)):
    return [(start + timedelta(days=i), D(v)) for i, v in enumerate(values)]


def test_the_change_h_sessions_later_and_none_past_the_end():
    closes = sessions(["100", "110", "121", "100"])
    assert forward_returns(closes, 2) == {date(2018, 1, 1): D("0.21"), date(2018, 1, 2): D("100") / D("110") - 1}


def test_only_days_at_least_h_sessions_apart_count_as_independent():
    index = {date(2018, 1, 1) + timedelta(days=i): i for i in range(10)}
    days = [date(2018, 1, 1) + timedelta(days=i) for i in (0, 1, 2, 5, 6, 9)]
    assert independent(days, index, h=3) == [days[0], days[3], days[5]]  # 0, then 5 (≥ 0+3), then 9 (≥ 5+3)


def test_a_group_says_its_samples_the_independent_ones_and_a_t_on_those_alone():
    index = {date(2018, 1, 1) + timedelta(days=i): i for i in range(40)}
    returns = {d: D("0.10") if i % 2 == 0 else D("-0.02") for d, i in index.items()}
    out = group_summary(list(index), returns, index, h=10)
    assert out["n"] == 40 and out["n_independent"] == 4 and out["win_rate"] == "0.5000"
    assert out["mean"] == "0.0400" and out["t"] is None  # the four independent days all gained 10%: no spread, no t
    assert group_summary([], returns, index, h=10) == {"n": 0, "n_independent": 0, "mean": None, "median": None, "win_rate": None, "t": None,
                                                    "p10": None, "p90": None, "dip_median": None, "dip_worst": None, "enough": False}


def test_a_lights_past_levels_are_worked_out_as_the_light_does_and_each_session_takes_the_level_known_that_day():
    """Kiểm tra ngưỡng đèn: oil's 30-day rise is green under 10%, yellow from 10%, red from 20% (domain.macro_signals)."""
    from investment_agent.domain.history_stats import light_groups
    days = [date(2018, 1, 1) + timedelta(days=i) for i in range(200)]
    oil = [(d, D(50) if i < 100 else D(65)) for i, d in enumerate(days)]       # +30% on day 100: red for thirty days, then flat
    closes = [(d, D(1000 + i)) for i, d in enumerate(days)]
    out = light_groups("oil", {"factor_oil": oil}, closes, h=10)
    by = {g["level"]: g for g in out["groups"]}
    assert by["red"]["n"] == 30 and by["green"]["n"] > 100 and by["yellow"]["n"] == 0
    assert out["name"] == "Giá dầu WTI" and out["today"] == "green" and out["from"] == "2018-01-31"


def summary_input(lights_today=("green", "green", "green", "green"), indep=6, t="1.58"):
    """t: the test against the rest (t_rest); 2.57 is what 6 windows need, so 1.58 is unclear and 2.40 with 40 windows is clear."""
    need = "2.57" if indep == 6 else "2.02"
    group = lambda b, mean, ind=indep, tt=t: {"bucket": b, "label": ["Rẻ nhất", "Rẻ", "Giữa", "Đắt", "Đắt nhất"][b], "n": 500, "n_independent": ind,  # noqa: E731
                                               "mean": mean, "median": mean, "win_rate": "0.7857", "t": "9.99", "t_rest": tt, "t_need": need,
                                               "differs": abs(Decimal(tt)) >= Decimal(need), "halves": "same"}
    pe = {"h": 250, "groups": [group(0, "0.2058")] + [group(b, "0.05") for b in range(1, 5)], "all": {"mean": "0.1190", "n": 1725},
          "today": {"date": "2026-11-20", "pe": "10.65", "position": "0.02", "bucket": 0}}
    names = {"oil": "Giá dầu WTI", "usd": "Đồng USD (chỉ số rộng của Fed)", "us10y": "Lợi suất trái phiếu Mỹ 10 năm", "pe": "P/E VN-Index so với 5 năm"}
    lights = [{"id": k, "name": names[k], "today": lv, "all": {"mean": "0.0250"},
               "groups": [{"level": x, "n": 80, "n_independent": 11, "mean": "-0.0574", "t": "-1.20", "t_rest": "-1.20", "t_need": "2.20",
                           "differs": False, "halves": "flip"} for x in ("green", "yellow", "red")]}
              for k, lv in zip(names, lights_today)]
    conditions = [{"label": "Giá dầu tăng trong 3 tháng", "state": True}, {"label": "Lạm phát (CPI) tăng so với 3 tháng trước", "state": False},
                  {"label": "Tỷ giá USD/VND tăng hơn 1% trong 3 tháng", "state": None}]
    return {"h": 250, "pe": pe, "lights": lights}, conditions


def test_the_summary_says_todays_pe_group_its_past_and_how_little_it_rests_on():
    from investment_agent.domain.history_stats import history_summary
    stats, conditions = summary_input()
    text = history_summary(stats, conditions)
    assert text.startswith("Hôm nay P/E VN-Index 10,65, thuộc nhóm rẻ nhất so với 5 năm trước. ")
    assert ("Trong quá khứ, ở nhóm này VN-Index 250 phiên sau trung bình +20,6% (mọi lúc +11,9%), tăng ở 79% số lần; "
            "dựa trên 6 khoảng không chồng lấn nhưng chưa rõ khác các lúc còn lại (t = 1,58, cần 2,57), chưa đủ để coi là chắc. ") in text
    weak = history_summary(summary_input(indep=3)[0], conditions)
    assert "nhưng chỉ có 3 khoảng không chồng lấn, quá ít để coi là chắc. " in weak
    assert ("Cả 4 đèn có lịch sử dài (Giá dầu WTI, Đồng USD (chỉ số rộng của Fed), Lợi suất trái phiếu Mỹ 10 năm, P/E VN-Index so với 5 năm) "
            "đang ở mức bình thường. ") in text
    assert "Vĩ mô hôm nay: 1/2 điều kiện đã biết đang đúng (giá dầu tăng trong 3 tháng); 1 điều kiện chưa biết. " in text
    assert text.endswith("Chỉ mô tả quá khứ, không phải dự báo hay khuyến nghị.")


def test_the_summary_names_a_light_off_normal_with_its_past():
    from investment_agent.domain.history_stats import history_summary
    stats, conditions = summary_input(lights_today=("green", "red", "green", "green"), indep=40, t="2.40")
    text = history_summary(stats, conditions)
    assert ("Đèn Đồng USD (chỉ số rộng của Fed) đang ở mức nguy hiểm; trong quá khứ ở mức này VN-Index 250 phiên sau trung bình −5,7% "
            "(mọi lúc +2,5%), dựa trên 11 khoảng không chồng lấn nhưng chưa rõ khác các lúc còn lại (t = −1,2, cần 2,20), chưa đủ để coi là chắc. ") in text
    assert "40 khoảng không chồng lấn, khác các lúc còn lại (t = 2,4, cần 2,02), ổn định ở hai nửa lịch sử. " in text


def test_pe_days_fall_in_five_groups_by_where_they_sat_in_the_five_years_before():
    days = [date(2018, 1, 1) + timedelta(days=i) for i in range(700)]
    pe = [(d, D(10 + (i % 50) / 10)) for i, d in enumerate(days)]          # 10.0 … 14.9 over and over
    closes = [(d, D(1000 + i)) for i, d in enumerate(days)]
    out = pe_groups(pe, closes, h=20)
    assert [g["bucket"] for g in out["groups"]] == [0, 1, 2, 3, 4]
    assert sum(g["n"] for g in out["groups"]) < 700                         # the first 250 days have no five-year place yet
    assert out["today"]["bucket"] in range(5) and out["today"]["pe"] == "14.90"
    assert all(g["pe_low"] is not None for g in out["groups"])
    assert out["trend"] is not None and {"slope", "intercept", "r2"} <= set(out["trend"])


def test_the_summary_does_not_read_figures_from_too_few_windows():
    from investment_agent.domain.history_stats import history_summary
    stats, conditions = summary_input(indep=3)
    for g in stats["pe"]["groups"]:
        g["enough"] = False
    text = history_summary(stats, conditions)
    assert ("Ở nhóm này chỉ có 3 khoảng 250 phiên không chồng lấn: không đủ dữ liệu cho kỳ này. ") in text and "trung bình +20,6%" not in text

def test_the_summary_says_a_shock_of_the_latest_session_with_its_past():
    from investment_agent.domain.history_stats import history_summary
    stats, conditions = summary_input()
    g = lambda k, label, today, enough=True: {"id": k, "label": label, "events": 199, "today": today, "n": 199, "n_independent": 18,  # noqa: E731
                                              "enough": enough, "mean": "0.1003", "p10": "-0.5688", "dip_median": "-0.1733"}
    stats["shocks"] = {"groups": [g("drop3", "VN-Index giảm từ 3% trong một phiên", True), g("down5", "VN-Index giảm 5 phiên liền", False)],
                       "combos": [], "all": {"mean": "0.1536"}, "from": "2000-07-28"}
    text = history_summary(stats, conditions)
    assert ("Cú sốc hôm nay: VN-Index giảm từ 3% trong một phiên. Trong quá khứ, VN-Index giảm từ 3% trong một phiên: 199 lần từ 2000 "
            "(18 khoảng không chồng lấn), 250 phiên sau trung bình +10,0% (mọi lúc +15,4%), xấu thường gặp −56,9%, "
            "giảm sâu nhất trong kỳ trung vị −17,3%. Chỉ mô tả quá khứ") in text
    stats["shocks"]["groups"][0]["today"] = False
    assert "Cú sốc" not in history_summary(stats, conditions)


def _blocks(extra):
    """400 sessions, h = 10: a group on the first ten sessions of every twenty, the rest on the other ten. Both move 3% ± 2% by block,
    so a t against 0 is large for either; extra(i) is added to the group's change only."""
    index = {date(2018, 1, 1) + timedelta(days=i): i for i in range(400)}
    group = [d for d, i in index.items() if i % 20 < 10]
    rest = [d for d, i in index.items() if i % 20 >= 10]
    base = lambda i: D("0.03") + D("0.02") * (1 if (i // 20) % 2 else -1)  # noqa: E731
    returns = {d: base(i) + (extra(i) if i % 20 < 10 else 0) for d, i in index.items()}
    return group, rest, returns, index


def test_a_group_is_tested_against_the_rest_not_against_zero_owner_22_11_2026():
    """Kaizen 22/11/2026: VN-Index rises over time, so almost every group's mean is above 0; the question the page asks is whether
    the group differs from the other sessions. Welch's t on the independent windows of both, against the t its degrees of freedom need."""
    group, rest, returns, index = _blocks(lambda i: 0)
    out = group_summary(group, returns, index, h=10, rest=rest)
    assert abs(D(out["t"])) > 5  # against 0: looks strong
    assert out["t_rest"] == "0.00" and out["t_need"] == "2.02" and out["differs"] is False
    _, _, ahead, _ = _blocks(lambda i: D("0.05"))
    better = group_summary(group, ahead, index, h=10, rest=rest)
    assert better["differs"] is True and D(better["t_rest"]) > D(better["t_need"]) and better["halves"] == "same"
    assert "t_rest" not in group_summary(group, returns, index, h=10)  # no rest given (the every-session row): nothing to compare


def test_a_group_ahead_in_one_half_of_history_and_behind_in_the_other_is_said_to_flip():
    group, rest, returns, index = _blocks(lambda i: D("0.05") if i < 200 else D("-0.05"))
    assert group_summary(group, returns, index, h=10, rest=rest)["halves"] == "flip"


def test_too_few_windows_on_either_side_is_not_compared():
    group, rest, returns, index = _blocks(lambda i: D("0.05"))
    out = group_summary(group, returns, index, h=10, rest=rest[:30])  # the rest: 3 independent windows
    assert out["differs"] is None and out["t_rest"] is None and out["halves"] is None


def test_the_t_needed_follows_the_degrees_of_freedom():
    from investment_agent.domain.history_stats import t_needed
    assert [t_needed(df) for df in (4, 6, 10, 30, 1000)] == ["2.78", "2.45", "2.23", "2.04", "1.96"]


def test_the_summary_reads_the_test_against_the_rest_and_says_how_many_groups_were_tested():
    from investment_agent.domain.history_stats import evidence_text, history_summary
    g = {"n": 500, "n_independent": 6, "t_rest": "1.58", "t_need": "2.57", "differs": False, "halves": "same"}
    assert evidence_text(g) == "dựa trên 6 khoảng không chồng lấn nhưng chưa rõ khác các lúc còn lại (t = 1,58, cần 2,57), chưa đủ để coi là chắc"
    assert evidence_text({**g, "t_rest": "3.1", "differs": True}) == "6 khoảng không chồng lấn, khác các lúc còn lại (t = 3,1, cần 2,57), ổn định ở hai nửa lịch sử"
    assert evidence_text({**g, "t_rest": "3.1", "differs": True, "halves": "flip"}).endswith("nhưng đổi chiều giữa hai nửa lịch sử")
    assert evidence_text({**g, "t_need": "2.00"}).startswith("dựa trên 6 khoảng không chồng lấn nhưng chưa rõ khác các lúc còn lại (t = 1,58, cần 2,00)")
    assert evidence_text({**g, "differs": None, "t_rest": None}) == "dựa trên 6 khoảng không chồng lấn, chưa so được với các lúc còn lại"
    assert evidence_text({**g, "n_independent": 3}) == "nhưng chỉ có 3 khoảng không chồng lấn, quá ít để coi là chắc"
    stats, conditions = summary_input()
    stats["tested"] = 118
    text = history_summary(stats, conditions)
    assert ("Trang so 118 nhóm với các lúc còn lại; dù không có quan hệ thật, khoảng 6 nhóm vẫn vượt ngưỡng do ngẫu nhiên. "
            "Chỉ mô tả quá khứ, không phải dự báo hay khuyến nghị.") in text


def test_every_table_sets_each_group_against_the_other_sessions_of_the_same_table():
    from investment_agent.domain.history_states import states_table
    from investment_agent.domain.history_stats import light_groups, shock_groups
    days = [date(2018, 1, 1) + timedelta(days=i) for i in range(900)]
    closes = [(d, D(1000 + (i % 37) * 7 - (i % 11) * 5 + i)) for i, d in enumerate(days)]
    pe = [(d, D(10 + (i % 50) / 10)) for i, d in enumerate(days)]
    oil = [(d, D(50) if i % 200 < 150 else D(65)) for i, d in enumerate(days)]
    tables = [pe_groups(pe, closes, h=20)["groups"], light_groups("oil", {"factor_oil": oil}, closes, h=20)["groups"],
              shock_groups(closes, h=20)["groups"], shock_groups(closes, h=20)["combos"],
              states_table([(d, i % 90 < 45) for i, d in enumerate(days)], [(d, i % 60 < 20) for i, d in enumerate(days)], closes, h=20)["rows"]]
    for groups in tables:
        assert all({"t_rest", "t_need", "differs", "halves"} <= set(g) for g in groups)
    assert any(g["differs"] is not None for g in tables[0])
    assert "t_rest" not in pe_groups(pe, closes, h=20)["all"]  # the every-session row is what the groups are read against


def test_tested_counts_the_groups_set_against_the_rest():
    from investment_agent.domain.history_stats import tested_groups
    g = lambda d: {"differs": d}  # noqa: E731
    stats = {"pe": {"groups": [g(True), g(None), g(False)]}, "lights": [{"groups": [g(False), g(None)]}],
             "shocks": {"groups": [g(True)], "combos": [g(None), g(False)]}}
    assert tested_groups(stats) == 5
