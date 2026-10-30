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
