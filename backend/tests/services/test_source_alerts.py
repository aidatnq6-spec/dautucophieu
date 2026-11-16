import json

from investment_agent.services.source_alerts import STATE, check_sources, source_view

LABELS = {"vn_retail_yoy": ("Cục Thống kê (nso.gov.vn)", "Bán lẻ so cùng kỳ"), "vn_trade_balance": ("Cục Thống kê (nso.gov.vn)", "Cán cân thương mại"),
          "wti": ("OilPrice", "Giá dầu WTI")}


def run(tmp_path, at, results):
    (tmp_path / "macro").mkdir(exist_ok=True)
    (tmp_path / "macro" / "_last_run.json").write_text(json.dumps({"at": at, "results": results}), encoding="utf-8")


def test_a_source_failing_three_runs_in_a_row_is_told_once_grouped_by_source(tmp_path):
    sent = []
    send = lambda text: sent.append(text) or True  # noqa: E731
    down = {"vn_retail_yoy": "error:ConnectError", "vn_trade_balance": "error:ConnectError", "wti": "ok"}
    for i, at in enumerate(("2026-11-16T00:36:00+00:00", "2026-11-16T01:34:00+00:00")):
        run(tmp_path, at, down)
        assert check_sources(tmp_path, send=send, labels=LABELS)["new"] == 0
    run(tmp_path, "2026-11-16T08:30:00+00:00", down)
    out = check_sources(tmp_path, send=send, labels=LABELS)
    assert out == {"status": "ok", "new": 2, "recovered": 0, "sent": True}
    assert sent == ["⚠️ Nguồn số liệu lỗi từ 3 lượt liên tiếp\n"
                    "• Cục Thống kê (nso.gov.vn): Bán lẻ so cùng kỳ, Cán cân thương mại — lỗi kết nối (ConnectError) từ 07:36 16/11/2026\n"
                    "Số đã lưu vẫn giữ; phần mềm tự thử lại ở các lượt sau."]
    run(tmp_path, "2026-11-16T13:00:00+00:00", down)
    assert check_sources(tmp_path, send=send, labels=LABELS)["new"] == 0 and len(sent) == 1  # told once while it lasts


def test_the_same_run_is_not_counted_twice_and_a_recovery_is_told(tmp_path):
    sent = []
    send = lambda text: sent.append(text) or True  # noqa: E731
    for at in ("2026-11-16T00:00:00+00:00", "2026-11-16T01:00:00+00:00", "2026-11-16T02:00:00+00:00"):
        run(tmp_path, at, {"wti": "error:HTTPStatusError"})
        check_sources(tmp_path, send=send, labels=LABELS)
        check_sources(tmp_path, send=send, labels=LABELS)  # the step run again without a new macro run: nothing counted
    assert len(sent) == 1
    run(tmp_path, "2026-11-16T03:00:00+00:00", {"wti": "ok"})
    assert check_sources(tmp_path, send=send, labels=LABELS)["recovered"] == 1
    assert sent[-1] == "✅ Nguồn số liệu đã lấy được trở lại\n• OilPrice: Giá dầu WTI"
    assert json.loads((tmp_path / "alerts" / STATE).read_text(encoding="utf-8"))["keys"] == {}


def test_a_note_telegram_did_not_take_is_tried_again_next_run(tmp_path):
    for at in ("2026-11-16T00:00:00+00:00", "2026-11-16T01:00:00+00:00", "2026-11-16T02:00:00+00:00"):
        run(tmp_path, at, {"wti": "error:ConnectError"})
        check_sources(tmp_path, send=lambda text: False, labels=LABELS)
    sent = []
    run(tmp_path, "2026-11-16T03:00:00+00:00", {"wti": "error:ConnectError"})
    assert check_sources(tmp_path, send=lambda text: sent.append(text) or True, labels=LABELS)["new"] == 1 and len(sent) == 1


def test_the_settings_view_lists_failing_sources_with_their_count(tmp_path):
    run(tmp_path, "2026-11-16T00:36:00+00:00", {"vn_retail_yoy": "error:ConnectError", "wti": "ok"})
    check_sources(tmp_path, send=lambda text: True, labels=LABELS)
    v = source_view(tmp_path, labels=LABELS)
    assert v == {"last_run": "2026-11-16T00:36:00+00:00", "checked": 2, "failing": [
        {"key": "vn_retail_yoy", "source": "Cục Thống kê (nso.gov.vn)", "label": "Bán lẻ so cùng kỳ", "fails": 1, "since": "2026-11-16T00:36:00+00:00",
         "error": "ConnectError", "alerted": False}]}
    assert source_view(tmp_path / "none", labels=LABELS) == {"last_run": None, "checked": 0, "failing": []}
