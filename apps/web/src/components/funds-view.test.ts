import { describe, expect, it } from "vitest";
import { coveredText, mineNotes, orderFunds, returnText, runUpCheck, scoreView } from "./funds-view";

describe("returnText", () => {
  it("shows a percentage return with its sign, and a dash when the source has none", () => {
    expect(returnText("-9.64")).toBe("−9,64%");
    expect(returnText("47.02")).toBe("+47,02%");
    expect(returnText("0")).toBe("0,00%");
    expect(returnText(null)).toBe("—");
  });
});

describe("mineNotes", () => {
  it("warns about too few funds, a single kind and funds counted at cost", () => {
    const notes = mineNotes({ groups: [{ kind: "BOND", value: "1000", share: "1", funds: ["VFF"] }], total: "1000", fund_count: 1, at_cost: ["GONE"],
      notes: ["fewer_than_3", "single_kind"] });
    expect(notes).toEqual(["Bạn đang giữ 1 quỹ: ít hơn 3 quỹ thì một quỹ đi sai hướng ảnh hưởng lớn đến cả phần quỹ.",
      "Toàn bộ nằm trong một nhóm (Trái phiếu): chưa có nhóm khác để cân lại khi thị trường đổi chiều.",
      "Chưa có NAV của GONE: tính theo vốn đã mua và chưa rõ nhóm."]);
    expect(mineNotes({ groups: [], total: "0", fund_count: 0, at_cost: [], notes: [] })).toEqual([]);
  });
});

describe("runUpCheck", () => {
  const base = { code: "DCDS", name: "Quỹ", kind: "STOCK" as const, manager: null, fee: null, nav: "100", date: "2026-11-13", held: false, beats_deposit: null,
    returns: { ytd: null, m1: null, m3: null, m6: "21.5", m12: "30.2", m36: null, m60: null, annual36: null } };
  it("places the fund in its kind and warns when its six months are in the top quarter", () => {
    const warn = runUpCheck({ ...base, rank: { m6: { rank: 2, of: 35 }, m12: { rank: 5, of: 30 } }, run_up: true });
    expect(warn.warn).toBe(true);
    expect(warn.text).toContain("DCDS 6 tháng +21,50%, cao thứ 2/35 quỹ cổ phiếu; 12 tháng +30,20%, cao thứ 5/30 quỹ cổ phiếu (NAV ngày 13/11/2026).");
    expect(warn.text).toContain("Quỹ vừa tăng mạnh");
    expect(runUpCheck({ ...base, rank: { m6: { rank: 20, of: 35 }, m12: null }, run_up: false }).warn).toBe(false);
  });
  it("says it cannot check a fund without returns", () => {
    expect(runUpCheck({ ...base, returns: null, run_up: null }).text).toContain("chưa kiểm tra được");
  });
});

describe("coveredText", () => {
  it("names the month and how much of each fund its published holdings cover", () => {
    expect(coveredText({ DCDS: { as_of: "2026-10", stocks: "55.73", bonds: "0" }, VIBF: { as_of: "2026-09", stocks: "18.62", bonds: "30.1" } }))
      .toBe("DCDS 10/2026: cổ phiếu công bố 55,7% NAV; VIBF 09/2026: cổ phiếu công bố 18,6% NAV, trái phiếu 30,1%");
  });
});

describe("scoreView", () => {
  it("shows the score, its change since last month and what was counted", () => {
    const s = { score: "62.5", parts: { returns: "75", fee: "50", risk: null }, counted: ["returns", "fee"], risk_days: 3, peers: 35,
      trend: { previous: "60", change: "2.5" } };
    expect(scoreView(s)).toEqual({ text: "63", arrow: "▲2,5", title: "hiệu suất 75, phí 50; rủi ro chưa tính (có 3 ngày NAV, cần 120)" });
    expect(scoreView({ ...s, trend: { previous: "70", change: "-7.5" } }).arrow).toBe("▼7,5");
    expect(scoreView({ ...s, score: null, peers: 1 }).title).toBe("Quỹ duy nhất trong nhóm: không so được");
    expect(scoreView(null).text).toBe("—");
  });
});


describe("orderFunds", () => {
  const fund = (code: string, kind: "STOCK" | "BOND", score: string | null, m12: string | null, m36: string | null, fee: string, held = false) => ({
    code, name: code, kind, manager: null, fee, nav: "1", date: "2026-11-13", held, beats_deposit: null,
    returns: { ytd: null, m1: null, m3: null, m6: null, m12, m36, m60: null, annual36: null },
    score: score === null ? null : { score, parts: { returns: null, fee: null, risk: null }, counted: [], risk_days: 0, peers: 9, trend: null } });
  const funds = [fund("NEW", "STOCK", "99", "20", null, "1"), fund("OLD", "STOCK", "70", "5", "40", "1.5"), fund("BEST", "STOCK", "90", "4", "30", "2"),
    fund("MINE", "STOCK", "10", "1", "10", "1.9", true), fund("BND", "BOND", "50", "6", "20", "0.5")];
  it("puts the owner's funds first, then funds with three years before new ones, by score within each kind", () => {
    expect(orderFunds(funds, "score", true).list.map((f) => f.code)).toEqual(["MINE", "BEST", "OLD", "NEW", "BND"]);
    expect(orderFunds(funds, "score", false).list.map((f) => f.code)).toEqual(["BEST", "OLD", "MINE", "NEW", "BND"]);
  });
  it("sorts by the lowest fee and marks the top three of each kind", () => {
    const o = orderFunds(funds, "fee", false);
    expect(o.list.map((f) => f.code)).toEqual(["OLD", "MINE", "BEST", "NEW", "BND"]);
    expect(o.top).toEqual({ NEW: 1, OLD: 2, MINE: 3, BND: 1 });
  });
});
