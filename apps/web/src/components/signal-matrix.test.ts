import { describe, expect, it } from "vitest";
import { GROUPS, groupState, matrixRows, tone } from "./signal-matrix";

const row = (symbol: string, values: Record<string, string | string[] | null>, sector = "Ngân hàng") => ({ symbol, sector, values, missing: {} });
const [value, fundamental, flow] = GROUPS;

describe("tone", () => {
  it("reads each signal in its own direction, and an overbought RSI as neither", () => {
    expect(tone("verdict", "cheap")).toBe(1);
    expect(tone("verdict", "expensive")).toBe(-1);
    expect(tone("quality", "medium")).toBe(0);
    expect(tone("foreign20", "sell")).toBe(-1);
    expect(tone("rsi_d", "overbought")).toBe(0);
    expect(tone("chain", ["tailwind", "headwind"])).toBe(0);
    expect(tone("chain", ["tailwind"])).toBe(1);
    expect(tone("macd_w", null)).toBeNull();
  });
});

describe("groupState", () => {
  it("is the side with more signals, and none when no signal in the group has data", () => {
    expect(groupState(flow, row("A", { foreign20: "buy", macd_w: "up", macd_d: "down" }).values)).toBe(1);
    expect(groupState(flow, row("A", { foreign20: "buy", macd_w: "down" }).values)).toBe(0);
    expect(groupState(fundamental, row("A", { quality: "weak", chain: null }).values)).toBe(-1);
    expect(groupState(value, row("A", {}).values)).toBeNull();
  });
});

describe("matrixRows", () => {
  const rows = [row("BBB", { verdict: "cheap", quality: "strong", foreign20: "sell" }), row("AAA", { verdict: "cheap", quality: "strong", foreign20: "buy" }),
    row("CCC", { verdict: "expensive" }, "Thép"), row("DDD", {})];
  it("puts the tickers most groups agree on first, the fewest against next, then by name; no score is added up", () => {
    const out = matrixRows(rows, { minGroups: 0, sector: "" });
    expect(out.map((r) => r.symbol)).toEqual(["AAA", "BBB", "DDD", "CCC"]);
    expect(out[0]).toMatchObject({ good: 3, bad: 0 });
    expect(out[1]).toMatchObject({ good: 2, bad: 1 });
  });
  it("narrows to tickers with enough groups agreeing, and to one sector", () => {
    expect(matrixRows(rows, { minGroups: 3, sector: "" }).map((r) => r.symbol)).toEqual(["AAA"]);
    expect(matrixRows(rows, { minGroups: 0, sector: "Thép" }).map((r) => r.symbol)).toEqual(["CCC"]);
  });
});
