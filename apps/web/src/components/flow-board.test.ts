import { describe, expect, it } from "vitest";
import { changeText, leftOut, type ChainReturn } from "./chain-returns";
import { foreignText, yearPosition, type FlowRow } from "./flow-board";

const row = (over: Partial<FlowRow>): FlowRow => ({ symbol: "AAA", held: false, date: "2026-11-20", close: "11000", pct: "0.01", volume: 1, volume_ratio: "1.00",
  range_position: "0.5", foreign_net_bn: null, foreign_run: null, high_52w: null, low_52w: null, ma20: null, ma50: null, flags: [], missing: [], ...over });

describe("Dòng tiền & kỹ thuật", () => {
  it("writes the foreign net with its run", () => {
    expect(foreignText(row({ foreign_net_bn: "1.5", foreign_run: 6 }))).toBe("+1,5 tỷ · gom 6 phiên");
    expect(foreignText(row({ foreign_net_bn: "-0.25", foreign_run: -2 }))).toBe("−0,3 tỷ · xả 2 phiên");
    expect(foreignText(row({}))).toBe("—");
  });

  it("places the close between the 52-week low and high, or says nothing without a year", () => {
    expect(yearPosition(row({ close: "15000", low_52w: "10000", high_52w: "20000" }))).toBe(0.5);
    expect(yearPosition(row({}))).toBeNull();
  });
});

describe("Hiệu suất theo kỳ", () => {
  it("writes a change with one decimal, or a dash when no member has it", () => {
    expect(changeText({ change: "0.0523", n: 3 })).toBe("+5,2%");
    expect(changeText({ change: "-0.1", n: 3 })).toBe("−10,0%");
    expect(changeText({ change: null, n: 0 })).toBe("—");
  });

  it("names the members left out and why", () => {
    const c = { no_data: ["ZZZ"], stale: ["OLD"] } as unknown as ChainReturn;
    expect(leftOut(c)).toBe("chưa có giá: ZZZ · giá cũ: OLD");
    expect(leftOut({ no_data: [], stale: [] } as unknown as ChainReturn)).toBeNull();
  });
});
