import copy
import json
from datetime import date, timedelta

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.leading import MacroStore
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call  # Clock date: 2027-01-15

SOURCE = {"title": "Câu chuyện đầu tư HT1", "publisher": "ACBS", "date": "2026-10-28", "url": "https://acbs.com.vn/x.pdf"}
REF = [{"source": "acbs-ht1", "page": 1}]
ITEM = {"name": "Than", "note": None, "share": None, "basis": None, "refs": REF}
CHAIN = {"id": "x", "name": "X", "icb": "Tài nguyên Cơ bản", "status": "draft", "symbols": [], "stages": {"input": [ITEM], "middle": [ITEM], "output": [ITEM]},
         "factors": [None, {"id": "f", "label": "Yếu tố", "stage": "input", "indicator": None, "when_up": "bad", "weight": "minor", "share": None,
                            "why": "lý do", "refs": REF}]}

TODAY = date(2027, 1, 15)


def chain(cid, symbols, status, factors):
    c = copy.deepcopy(CHAIN)
    c.update(id=cid, name=cid.title(), symbols=symbols, status=status)
    c["factors"] = [{**copy.deepcopy(CHAIN["factors"][1]), "id": fid, "indicator": ind, "when_up": up, "weight": w, "share": None}
                    for fid, ind, up, w in factors]
    return c


def client_for(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("HPG\nVCB\nFPT\n", encoding="utf-8")
    store = MacroStore(tmp_path)
    store.upsert("wti", [(TODAY - timedelta(days=35), "60"), (TODAY - timedelta(days=1), "66")], entry="auto")              # +10%: up
    store.upsert("vn_interbank_on", [(TODAY - timedelta(days=35), "5"), (TODAY - timedelta(days=1), "4.5")], entry="auto")  # −0.5 pp: down
    doc = {"version": "t", "sources": {"acbs-ht1": SOURCE}, "chains": [
        chain("steel", ["HPG"], "approved", [("oil", "wti", "bad", "major"), ("rates", "vn_interbank_on", "bad", "minor")]),   # bad 3, good 2
        chain("bank", ["VCB"], "approved", [("rates", "vn_interbank_on", "bad", "major"), ("coal", None, "bad", "small")]),   # good 3, unknown 1
        chain("draft", ["ZZZ"], "draft", [("oil", "wti", "good", "major")]),
    ]}
    path = tmp_path / "value-chains.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    app.state.value_chains_path = path
    client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    return lambda: call(client, clock, "GET", "/internal/market/value-chains").json()


def setup(tmp_path):
    """(get, put) against one app; put sends the approval for a chain."""
    (tmp_path / "market-symbols.txt").write_text("HPG\n", encoding="utf-8")
    doc = {"version": "t", "sources": {"acbs-ht1": SOURCE}, "chains": [chain("steel", ["HPG"], "draft", [("oil", "wti", "bad", "major")])]}
    path = tmp_path / "value-chains.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    MacroStore(tmp_path).upsert("wti", [(TODAY - timedelta(days=35), "60"), (TODAY - timedelta(days=1), "66")], entry="auto")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    app.state.value_chains_path = path
    client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    get = lambda: call(client, clock, "GET", "/internal/market/value-chains").json()  # noqa: E731
    put = lambda cid, body: call(client, clock, "PUT", f"/internal/market/value-chains/{cid}/approval", body)  # noqa: E731
    return get, put, path, doc


def test_the_owner_approves_a_chain_in_the_app_and_a_content_change_asks_again(tmp_path):
    get, put, path, doc = setup(tmp_path)
    steel = get()["chains"][0]
    assert (steel["status"], steel["label"], steel["approval"]) == ("draft", None, None) and len(steel["fingerprint"]) == 16
    stale = put("steel", {"approved": True, "fingerprint": "0" * 16, "note": None})
    assert stale.status_code == 409 and stale.json()["code"] == "content_changed"  # the page showed other content
    assert put("nope", {"approved": True, "fingerprint": steel["fingerprint"], "note": None}).status_code == 404
    done = put("steel", {"approved": True, "fingerprint": steel["fingerprint"], "note": "Đã đọc ACBS"})
    assert done.status_code == 200
    steel = done.json()["chains"][0]
    assert (steel["status"], steel["label"]) == ("approved", "headwind")
    assert steel["approval"] == {"on": "2027-01-15", "note": "Đã đọc ACBS", "by": "app", "stale": False}
    # the chain's content changes: back to Chưa duyệt, and the page says the earlier approval was for other content
    doc["chains"][0]["factors"][0]["why"] = "Lý do mới"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    steel = get()["chains"][0]
    assert (steel["status"], steel["label"], steel["approval"]["stale"], steel["approval"]["on"]) == ("draft", None, True, "2027-01-15")
    put("steel", {"approved": True, "fingerprint": steel["fingerprint"], "note": None})
    undone = put("steel", {"approved": False, "fingerprint": steel["fingerprint"], "note": None}).json()["chains"][0]
    assert (undone["status"], undone["approval"]) == ("draft", None)


def test_event_factors_stay_off_the_bar_and_a_chain_of_events_alone_has_too_little_data(tmp_path):
    get, put, path, doc = setup(tmp_path)
    event = {**copy.deepcopy(CHAIN["factors"][1]), "id": "tariff", "kind": "event", "weight": "major"}
    doc["chains"][0].update(status="approved")
    doc["chains"][0]["factors"].append(event)                                                          # steel: oil (major, bad) + an event
    doc["chains"].append({**chain("seafood", ["VHC"], "approved", []), "factors": [{**event}]})       # events only
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    steel, seafood = sorted(get()["chains"], key=lambda c: c["id"] != "steel")
    assert steel["score"] == {"good": "0.0000", "bad": "1.0000", "neutral": "0.0000", "unknown": "0.0000"} and steel["measured"] == 1
    assert steel["factors"][-1]["status"] == "event" and steel["label"] == "headwind"
    assert seafood["measured"] == 0 and seafood["label"] == "insufficient"


def test_a_chain_approved_in_the_config_needs_no_approval_in_the_app(tmp_path):
    get, put, path, doc = setup(tmp_path)
    doc["chains"][0]["status"] = "approved"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    steel = get()["chains"][0]
    assert (steel["status"], steel["approval"]) == ("approved", {"on": None, "note": None, "by": "config", "stale": False})
    assert put("steel", {"approved": False, "fingerprint": steel["fingerprint"], "note": None}).status_code == 422


def test_value_chains_are_read_against_stored_series_and_ordered(tmp_path):
    body = client_for(tmp_path)()
    assert [c["id"] for c in body["chains"]] == ["bank", "steel", "draft"]  # Thuận gió, then Ngược gió (bad − good = 0.20 exactly), drafts last
    bank, steel, draft = body["chains"]
    assert bank["label"] == "tailwind" and bank["score"] == {"good": "0.7500", "bad": "0.0000", "neutral": "0.0000", "unknown": "0.2500"}
    assert steel["label"] == "headwind" and steel["score"]["bad"] == "0.6000" and steel["score"]["good"] == "0.4000"
    assert draft["label"] is None and draft["status"] == "draft"
    oil = steel["factors"][0]
    assert (oil["status"], oil["reading"]["direction"], oil["reading"]["change"], oil["indicator_label"]) == ("bad", "up", "0.1", "Giá dầu WTI")
    assert bank["factors"][1]["status"] == "unknown" and bank["factors"][1]["reading"] is None
    assert bank["symbols"] == [{"symbol": "VCB", "held": False}]
    assert body["uncovered"] == ["FPT"] and body["sources"]["acbs-ht1"]["publisher"] == "ACBS"


def test_each_factor_that_cannot_be_read_says_why(tmp_path):
    """The card names what is missing: no series in the app, no stored figure, a figure older than its limit, or a single figure."""
    (tmp_path / "market-symbols.txt").write_text("HPG\n", encoding="utf-8")
    store = MacroStore(tmp_path)
    store.upsert("com_iron_ore", [(date(2026, 9, 1), "100"), (date(2026, 10, 1), "101")], entry="auto")   # 106 days before TODAY: past 75
    store.upsert("vn_retail_yoy", [(date(2026, 12, 31), "8.4")], entry="auto")                             # one month only
    store.upsert("wti", [(TODAY - timedelta(days=35), "60"), (TODAY - timedelta(days=1), "66")], entry="auto")
    doc = {"version": "t", "sources": {"acbs-ht1": SOURCE}, "chains": [chain("steel", ["HPG"], "approved", [
        ("coke", None, "bad", "major"), ("ore", "com_iron_ore", "bad", "major"), ("port", "vn_retail_yoy", "good", "minor"),
        ("sugar", "com_sugar", "bad", "small"), ("oil", "wti", "bad", "small")])]}
    path = tmp_path / "value-chains.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     data_dir=tmp_path)
    app.state.value_chains_path = path
    client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000))
    factors = {f["id"]: f for f in call(client, clock, "GET", "/internal/market/value-chains").json()["chains"][0]["factors"]}
    assert factors["coke"]["missing"] == {"reason": "no_series", "max_age_days": None}
    assert factors["ore"]["missing"] == {"reason": "stale", "max_age_days": 75}
    assert factors["port"]["missing"]["reason"] == "one_point"
    assert factors["sugar"]["missing"]["reason"] == "no_data"
    assert factors["oil"]["missing"] is None


def test_daily_and_weekly_chain_series_get_their_own_age_limits():
    from investment_agent.market.value_chains import CHAIN_MAX_AGE_DAYS, COMMODITY_LABELS
    assert CHAIN_MAX_AGE_DAYS == {"vn_hydro_inflow_yoy": 7, "com_container_scfi": 14, "com_tanker_ctfi": 7, "com_steel_hrc": 10}
    assert all(k in COMMODITY_LABELS for k in ("vn_hydro_inflow_yoy", "com_dairy", "com_container_scfi", "com_tanker_ctfi", "com_steel_hrc"))
