import { describe, expect, it } from "vitest";
import { coveredText, mineNotes, returnText, runUpCheck } from "./funds-view";

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
