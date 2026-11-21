import { describe, expect, it } from "vitest";
import { dayTone, sectorGroups, type HeatRow } from "./session-maps";

const r = (symbol: string, sector: string, value: string, pct = "0.01"): HeatRow => ({ symbol, sector, pct, value_mn: value, held: false });

describe("Bản đồ nhiệt phiên", () => {
  it("colours a change in three steps each way, grey when unchanged", () => {
    expect(dayTone("0.005")).toBe("am-g1");
    expect(dayTone("0.015")).toBe("am-g2");
    expect(dayTone("-0.069")).toBe("am-r3");
    expect(dayTone("0")).toBe("am-flat");
  });

  it("groups stocks by sector, the largest matched value first at both levels", () => {
    const groups = sectorGroups([r("VCB", "Ngân hàng", "100"), r("VIC", "Bất động sản", "500"), r("TCB", "Ngân hàng", "300")]);
    expect(groups.map((g) => g.sector)).toEqual(["Bất động sản", "Ngân hàng"]);
    expect(groups[1].rows.map((x) => x.symbol)).toEqual(["TCB", "VCB"]);
    expect(groups[1].value).toBe(400);
  });
});
