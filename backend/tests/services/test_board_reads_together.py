from investment_agent.services import holdings_view as hv


def test_the_banks_entered_figures_are_fetched_together_before_they_are_read(monkeypatch, tmp_path):
    fetched = []
    monkeypatch.setattr(hv, "prefetch", lambda repo, owner, records: fetched.append(list(records)))
    monkeypatch.setattr(hv, "read_version", lambda *a: None)
    sectors = {"AAA": "Ngân hàng", "BBB": "Thép", "CCC": "Ngân hàng"}
    assert hv._bank_figures(object(), "owner", tmp_path, ["AAA", "BBB", "CCC"], sectors) == {}
    assert fetched == [[("settings", "bank_figures_AAA"), ("settings", "bank_figures_CCC")]]


def test_without_a_repository_nothing_is_fetched(monkeypatch, tmp_path):
    monkeypatch.setattr(hv, "prefetch", lambda *a: (_ for _ in ()).throw(AssertionError("no repository to read")))
    assert hv._bank_figures(None, "owner", tmp_path, ["AAA"], {"AAA": "Ngân hàng"}) == {}
