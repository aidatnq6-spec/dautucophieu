import { describe, expect, it } from "vitest";
import { cellView, rankText } from "./sectors-view";

const cell = { quarter: "2026-Q3", profit_yoy: null as string | null, profit_turn: null as string | null, cfo: null as string | null, debt_yoy: null as string | null };

describe("cellView", () => {
  it("colours profit growth from deep red to deep green", () => {
    expect(cellView("profit", { ...cell, profit_yoy: "0.6000" }, 0)).toEqual({ text: "+60%", tone: "g3" });
    expect(cellView("profit", { ...cell, profit_yoy: "0.0500" }, 0)).toEqual({ text: "+5%", tone: "g1" });
    expect(cellView("profit", { ...cell, profit_yoy: "-0.9000" }, 0)).toEqual({ text: "−90%", tone: "r3" });
    expect(cellView("profit", { ...cell, profit_turn: "to_profit" }, 0)).toEqual({ text: "lãi lại", tone: "g2" });
    expect(cellView("profit", { ...cell, profit_turn: "to_loss" }, 0)).toEqual({ text: "lỗ", tone: "r3" });
    expect(cellView("profit", cell, 0)).toEqual({ text: "—", tone: "" });
  });
  it("colours cash from operations by sign, stronger for the ticker's larger quarters", () => {
    expect(cellView("cfo", { ...cell, cfo: "900000000000" }, 1e12)).toEqual({ text: "900", tone: "g3" });
    expect(cellView("cfo", { ...cell, cfo: "-100000000000" }, 1e12)).toEqual({ text: "−100", tone: "r1" });
  });
  it("colours rising borrowing red and falling borrowing green", () => {
    expect(cellView("debt", { ...cell, debt_yoy: "1.2000" }, 0)).toEqual({ text: "+120%", tone: "r3" });
    expect(cellView("debt", { ...cell, debt_yoy: "-0.2000" }, 0)).toEqual({ text: "−20%", tone: "g2" });
  });
});

describe("rankText", () => {
  it("says how rarely the sector was this cheap, and since when it has not been", () => {
    expect(rankText({ month: "2026-11", value: "1.24", count: 9, lowest_since: "2020-04", rank: "0.0220", months: 92 }, "2019-04"))
      .toBe("P/B trung vị 11/2026: 1,24 lần (9 mã). Thấp nhất kể từ 04/2020; chỉ 2% số tháng từ 04/2019 thấp hơn mức này.");
    expect(rankText({ month: "2026-11", value: "0.98", count: 7, lowest_since: "2026-10", rank: "0.0152", months: 199 }, "2010-05"))
      .toBe("P/B trung vị 11/2026: 0,98 lần (7 mã). Chỉ 2% số tháng từ 05/2010 thấp hơn mức này.");
    expect(rankText({ month: "2026-11", value: "0.70", count: 3, lowest_since: null, rank: "0.0000", months: 40 }, "2023-08"))
      .toContain("Thấp nhất từ trước đến nay (từ 08/2023)");
  });
});
