from datetime import datetime

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call
from test_overview_route import MARKET, buy_fpt, setup_owner  # FPT bought 100 × 50,000 on 05/01/2027; the clock reads 15/01/2027


def client(tmp_path, repo=True):
    series = SeriesStore(tmp_path / "trend-sources")
    series.upsert("FPT-1d", [(datetime(2027, 1, d), v) for d, v in ((5, "50"), (6, "70"), (7, "60"), (8, "55"))])  # thousand đồng
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock,
                     personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()) if repo else None, market=MARKET, data_dir=tmp_path)
    c = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    if repo:
        setup_owner(c, clock)
        buy_fpt(c, clock)
    return c, clock


def test_each_holding_and_the_portfolio_show_the_peak_gain_and_what_went_back(tmp_path):
    c, clock = client(tmp_path)
    body = call(c, clock, "GET", "/internal/giveback").json()
    assert body["thresholds"] == {"min_gain": None, "share": None} and body["as_of"] == "2027-01-15"
    fpt = body["rows"][0]
    assert fpt["symbol"] == "FPT" and fpt["peak"] == {"gain": "2000000", "ratio": "0.4000", "on": "2027-01-06"}
    assert fpt["given_back"] == "1500000" and fpt["share"] == "0.7500"
    assert body["portfolio"]["peak"]["gain"] == "2000000" and body["portfolio"]["missing"] == []
    assert body["goals"] == [] and body["goals_version"] == 0


def test_without_personal_store_it_is_unavailable(tmp_path):
    c, clock = client(tmp_path, repo=False)
    assert call(c, clock, "GET", "/internal/giveback").status_code == 503


def test_the_two_thresholds_are_set_together_in_the_portfolio_settings(tmp_path):
    c, clock = client(tmp_path)
    base = {"concentration_limit": "0.25", "journal_review_threshold": "0.15", "drawdown_threshold": "0.3"}
    ok = call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": {**base, "giveback_min_gain": "1.5", "giveback_share": "0.5"},
                                                                 "expected_version": 0, "request_id": "pf1"})
    assert ok.status_code == 200 and ok.json()["settings"]["giveback_min_gain"] == "1.5"
    assert call(c, clock, "GET", "/internal/giveback").json()["thresholds"] == {"min_gain": "1.5", "share": "0.5"}
    one = call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": {**base, "giveback_min_gain": "0.3"}, "expected_version": 1, "request_id": "pf2"})
    assert one.status_code == 422
    big = call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": {**base, "giveback_min_gain": "0.3", "giveback_share": "1.5"},
                                                                  "expected_version": 1, "request_id": "pf3"})
    assert big.status_code == 422
    cleared = call(c, clock, "PUT", "/internal/settings/portfolio", {"settings": base, "expected_version": 1, "request_id": "pf4"})
    assert cleared.status_code == 200 and cleared.json()["settings"]["giveback_min_gain"] is None


def test_goals_are_saved_with_their_version_and_each_says_whether_it_is_covered(tmp_path):
    c, clock = client(tmp_path)
    goals = [{"id": "g1", "name": "Mua xe", "amount": "6500000", "basis": "value", "created_on": "2027-01-15", "closed": None},
             {"id": "g2", "name": "Du lịch", "amount": "1000000", "basis": "gain", "created_on": "2027-01-15", "closed": None}]
    saved = call(c, clock, "PUT", "/internal/spend-goals", {"goals": goals, "expected_version": 0, "request_id": "sg1"})
    assert saved.status_code == 200
    body = saved.json()
    assert body["goals_version"] == 1
    car, trip = body["goals"]
    assert car["status"]["enough"] is False and car["status"]["short"] == "1000000"  # value 5 500 000 on 08/01
    assert car["status"]["last"] == {"from": "2027-01-06", "to": "2027-01-06", "excess": "500000"} and car["status"]["last_before_goal"] is True
    assert trip["status"]["enough"] is False and trip["status"]["last"]["from"] == "2027-01-06"
    stale = call(c, clock, "PUT", "/internal/spend-goals", {"goals": goals, "expected_version": 0, "request_id": "sg2"})
    assert stale.status_code == 409
    too_many = [{**goals[0], "id": f"g{i}"} for i in range(11)]
    assert call(c, clock, "PUT", "/internal/spend-goals", {"goals": too_many, "expected_version": 1, "request_id": "sg3"}).status_code == 422
    twice = [goals[0], goals[0]]
    assert call(c, clock, "PUT", "/internal/spend-goals", {"goals": twice, "expected_version": 1, "request_id": "sg4"}).status_code == 422
    zero = [{**goals[0], "amount": "0"}]
    assert call(c, clock, "PUT", "/internal/spend-goals", {"goals": zero, "expected_version": 1, "request_id": "sg5"}).status_code == 422
    closed = [{**goals[0], "closed": {"kind": "done", "on": "2027-01-15"}}]
    after = call(c, clock, "PUT", "/internal/spend-goals", {"goals": closed, "expected_version": 1, "request_id": "sg6"}).json()
    assert after["goals"][0]["closed"] == {"kind": "done", "on": "2027-01-15"}
