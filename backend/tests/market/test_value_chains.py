import copy
import json

import pytest
from pydantic import ValidationError

from investment_agent.market.value_chains import load_value_chains

SOURCE = {"title": "Câu chuyện đầu tư HT1", "publisher": "ACBS", "date": "2026-10-28",
          "url": "https://acbs.com.vn/acbsmedia/2026/10/HT1-Cau-chuyen-dau-tu-28102026-2.pdf"}
REF = [{"source": "acbs-ht1", "page": 1}]
CHAIN = {"id": "cement", "name": "Xi măng", "icb": "Xây dựng và Vật liệu", "status": "draft", "symbols": ["HT1"],
         "stages": {"input": [{"name": "Than", "note": None, "share": "0.35-0.40", "basis": "giá thành", "refs": REF}],
                    "middle": [{"name": "Nung clinker, nghiền xi măng", "note": None, "share": None, "basis": None, "refs": REF}],
                    "output": [{"name": "Đầu tư công", "note": None, "share": None, "basis": None, "refs": REF}]},
         "factors": [{"id": "coal", "label": "Giá than", "stage": "input", "indicator": "com_coal", "when_up": "bad", "weight": "major",
                      "share": "0.35-0.40", "why": "Than chiếm 35–40% giá thành", "refs": REF},
                     {"id": "rates", "label": "Lãi suất liên ngân hàng", "stage": "output", "indicator": "vn_interbank_on", "when_up": "bad",
                      "weight": "minor", "share": None, "why": "Lãi suất cao làm chậm xây dựng", "refs": REF}]}
DOC = {"version": "2026-10-30", "sources": {"acbs-ht1": SOURCE}, "chains": [CHAIN]}


def write(tmp_path, doc):
    path = tmp_path / "value-chains.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return path


def changed(edit):
    doc = copy.deepcopy(DOC)
    edit(doc)
    return doc


def test_a_sourced_chain_loads(tmp_path):
    chains = load_value_chains(write(tmp_path, DOC))
    assert chains.chains[0].factors[0].indicator == "com_coal" and chains.sources["acbs-ht1"].publisher == "ACBS"


@pytest.mark.parametrize("edit", [
    lambda d: d["chains"][0]["stages"]["input"][0].update(refs=[]),                         # an item without a source
    lambda d: d["chains"][0]["factors"][0].update(refs=[{"source": "nowhere", "page": 1}]),  # an unknown source
    lambda d: d["chains"][0]["factors"][1].update(indicator="gold_price"),                   # a series the app does not keep
    lambda d: d["chains"].append({**copy.deepcopy(CHAIN), "id": "cement-2"}),                # HT1 in two chains
    lambda d: d["chains"][0]["factors"][0].update(weight="small"),                           # 35–40% is chính, not nhỏ
    lambda d: d["chains"][0]["stages"].update(middle=[]),                                    # an empty stage
    lambda d: d["chains"][0].update(factors=[]),                                             # no factor at all
    lambda d: d["chains"][0].update(status="checked"),
    lambda d: d["sources"]["acbs-ht1"].update(date="28/10/2026"),
])
def test_unsourced_or_inconsistent_chains_are_rejected(tmp_path, edit):
    with pytest.raises((ValidationError, ValueError)):
        load_value_chains(write(tmp_path, changed(edit)))


def test_a_factor_without_a_stored_series_is_allowed(tmp_path):
    doc = changed(lambda d: d["chains"][0]["factors"][0].update(indicator=None))
    assert load_value_chains(write(tmp_path, doc)).chains[0].factors[0].indicator is None


def test_a_source_dated_by_month_alone_is_allowed(tmp_path):
    assert load_value_chains(write(tmp_path, changed(lambda d: d["sources"]["acbs-ht1"].update(date="2026-06")))).sources["acbs-ht1"].date == "2026-06"


def test_the_committed_config_loads():
    load_value_chains()


# The 50 watched tickers on 30/10/2026, as listed in the spec (data\ is not in Git).
WATCHED_2026_10_30 = ("MBB ACB BID CTG SHB STB TCB VCB EIB KDH VHM VIC KBC DXG NLG IJC MSN VNM VHC KDC SBT ANV PAN GVR DCM DPM PHR DPR "
                      "GAS REE NT2 HDG GMD PVT VSC HAH SSI HCM VND BMP CTD VCG FPT CMG MWG DGW HPG BVH PNJ PVD").split()


def test_the_committed_config_gives_every_watched_ticker_one_chain():
    chains = load_value_chains().chains
    owned = [s for c in chains for s in c.symbols]
    assert len(WATCHED_2026_10_30) == 50 and sorted(owned) == sorted(WATCHED_2026_10_30)
