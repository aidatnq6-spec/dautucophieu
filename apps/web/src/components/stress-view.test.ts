import { expect, it } from "vitest";
import { applyScenario } from "./stress-view";

const row = (symbol: string, over: Record<string, unknown> = {}) => ({ symbol, shares: 100, price: "60000", value: "6000000", cost: "50000", beta: "1.2",
  oil: null, usd: null, oil_note: "Quan hệ không rõ (|t| < 2)", usd_note: "Chưa đủ dữ liệu để đo", ...over });

it("prices a market fall by beta and names what could not be counted", () => {
  const out = applyScenario({ rows: [row("FPT"), row("HPG", { beta: null }), row("VCB", { price: null, value: null })], threshold: "0.30", tolerance: null },
    { market: -0.2, oil: 0, usd: 0 });
  expect(out.rows[0]).toMatchObject({ symbol: "FPT", move: -0.24, change: -1440000 });
  expect(out.total).toBe(-1440000);
  expect(out.pct).toBeCloseTo(-0.24);
  expect(out.excluded).toEqual([{ symbol: "HPG", reason: "Thiếu beta (VNDirect)" }, { symbol: "VCB", reason: "Chưa có giá" }]);
});

it("adds a clear factor relation and notes an unclear one as not counted", () => {
  const out = applyScenario({ rows: [row("FPT", { beta: null, oil: "-0.150" }), row("HPG")], threshold: "0.30", tolerance: null }, { market: 0, oil: 0.3, usd: 0 });
  expect(out.rows.find((r) => r.symbol === "FPT")).toMatchObject({ move: -0.045, notes: [] });
  expect(out.rows.find((r) => r.symbol === "HPG")).toMatchObject({ move: 0, notes: ["Dầu: chưa tính (Quan hệ không rõ (|t| < 2))"] });
});

it("compares with the owner's stated tolerance and the drawdown threshold", () => {
  const inputs = { rows: [row("FPT", { price: "40000", value: "4000000" })], threshold: "0.30", tolerance: { answer: "B", limit: "0.10", label: "x" } };
  const out = applyScenario(inputs, { market: -0.15, oil: 0, usd: 0 });
  expect(out.overTolerance).toBe(true);  // −18% against a stated 10%
  expect(out.rows[0].crossesThreshold).toBe(true);  // 40 000 × 0,82 = 32 800: 34,4% under the cost of 50 000, past 30%
  expect(applyScenario(inputs, { market: -0.1, oil: 0, usd: 0 }).rows[0].crossesThreshold).toBe(false);  // 35 200: −29,6%
  expect(applyScenario(inputs, { market: -0.05, oil: 0, usd: 0 }).overTolerance).toBe(false);
});
