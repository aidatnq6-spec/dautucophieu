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
