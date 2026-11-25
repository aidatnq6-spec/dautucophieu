"""The commands the schedule replaced with one note each are gone (owner, 21/11/2026): Việc tài chính hôm nay, Danh mục hôm nay and
Nhắc vĩ mô run their parts themselves, so the old one-part commands only invited sending a part twice."""

import sys

import pytest

from investment_agent import cli

GONE = ("deposit-alerts", "pyramid-alerts", "loan-alerts", "contribution-remind", "accumulation-remind", "buy-plan-check",
        "insider-alerts", "drawdown-check", "macro-signals", "liquidity-alerts")


@pytest.mark.parametrize("command", GONE)
def test_a_replaced_command_is_refused(command, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["investment_agent", command, "--data-dir", "data"])
    with pytest.raises(SystemExit) as stop:
        cli.main()
    assert stop.value.code == 2 and "invalid choice" in capsys.readouterr().err


@pytest.mark.parametrize("command,called", [("wealth-alerts", "wealth_alerts_cli"), ("portfolio-alerts", "portfolio_alerts_cli"),
                                            ("macro-alerts", "macro_alerts_cli")])
def test_the_combined_commands_remain(command, called, monkeypatch):
    seen = []
    monkeypatch.setattr(cli, called, lambda *a, **k: seen.append(a) or 0)
    argv = ["investment_agent", command, "--data-dir", "data"] + (["--calendar", "c.json"] if command == "portfolio-alerts" else [])
    monkeypatch.setattr(sys, "argv", argv)
    assert cli.main() == 0 and len(seen) == 1


def test_a_command_run_by_hand_prints_vietnamese_whatever_the_console_code_page(tmp_path):
    """Run by hand through a pipe, Windows gives cp1252, which has no Vietnamese letters: `industries` wrote its file, then failed printing
    "Bất động sản" and exited 1. The command surface writes UTF-8 instead; the scheduler already asks for it (jobs.step)."""
    import io
    from investment_agent.cli import _utf8_output
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252")
    _utf8_output(stream)
    stream.write("Bất động sản")
    stream.flush()
    assert raw.getvalue().decode("utf-8") == "Bất động sản"
    already = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    _utf8_output(already)  # left as it is
    assert already.encoding == "utf-8"
