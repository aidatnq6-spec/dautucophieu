import { expect, it } from "vitest";
import { baseText, proprietaryHead, recoveryHead, spreadText, streakText } from "./brief-market";

it("words the run of sessions, never giving a total for a run that reaches past the data", () => {
  expect(streakText({ direction: "up", sessions: 2, at_least: false, change: "41.11", pct: "0.0242" })).toBe("Tăng 2 phiên liên tiếp, +41,11 điểm (+2,42%)");
  expect(streakText({ direction: "down", sessions: 3, at_least: true, change: null, pct: null })).toBe("Giảm ít nhất 3 phiên liên tiếp");
  expect(streakText({ direction: "flat", sessions: 1, at_least: false, change: "0.00", pct: "0.0000" })).toBe("Đứng giá so với phiên trước");
  expect(streakText({ direction: null, sessions: 0, at_least: true, change: null, pct: null })).toBeNull();
});

it("compares a figure with the previous session and the 20 before", () => {
  expect(baseText({ change_pct: "-0.1425", ratio20: "1.11" })).toBe("−14,25% so với phiên trước · bằng 1,11 lần trung bình 20 phiên");
  expect(baseText({ change_pct: null, ratio20: "0.97" })).toBe("bằng 0,97 lần trung bình 20 phiên");
});

it("sets the equal-weight spread beside VN-Index and names an opposite direction", () => {
  const spread = { count: 358, mean_pct: "0.0030", median_pct: "0.0000" };
  expect(spreadText(spread, "0.0044")).toBe("Trung bình cộng các mã +0,30%, trung vị 0,00% (358 mã có giao dịch); VN-Index +0,44%");
  expect(spreadText(spread, "-0.0051")).toBe("Trung bình cộng các mã +0,30%, trung vị 0,00% (358 mã có giao dịch); VN-Index −0,51%, ngược chiều");
  expect(spreadText(spread, null)).toBe("Trung bình cộng các mã +0,30%, trung vị 0,00% (358 mã có giao dịch)");
  expect(spreadText({ count: 0, mean_pct: null, median_pct: null }, "0.01")).toBeNull();
});

it("counts the recovery conditions met and names those without figures", () => {
  expect(recoveryHead({ met: 2, known: 4, total: 4 })).toBe("2/4 điều kiện đạt");
  expect(recoveryHead({ met: 1, known: 3, total: 4 })).toBe("1/4 điều kiện đạt, 1 điều kiện chưa có số");
});

it("a base on fewer sessions or an older previous session says so (fix 25/11/2026)", () => {
  expect(baseText({ change_pct: "0.05", ratio20: "1.02", avg_sessions: 19, previous_session: "2026-11-23", previous_skipped: true }))
    .toBe("+5,00% so với phiên 23/11 · bằng 1,02 lần trung bình 19 phiên có số");
});

it("names Tự doanh's own session and how far VNDirect lags, and nothing when it is the brief's session", () => {
  expect(proprietaryHead({ date: "2026-11-23", lag_sessions: 3 })).toBe("Tự doanh — phiên 23/11/2026 (VNDirect chậm 3 phiên)");
  expect(proprietaryHead({ date: "2026-11-26", lag_sessions: 0 })).toBe("Tự doanh");
});

it("words a 20-session flow row with its own session, lag, sum and missing sessions", async () => {
  const { flowHead } = await import("./brief-market");
  const flow = { status: "ok" as const, date: "2026-11-23", lag_sessions: 3, net_bn: "357.51", sum_bn: "230.40", missing: 2, bars: [] };
  expect(flowHead(flow)).toEqual({ value: "+357,5 tỷ", tone: "positive", sub: "Phiên 23/11 (chậm 3 phiên) · 20 phiên +230 tỷ (thiếu 2 phiên)" });
  expect(flowHead({ ...flow, lag_sessions: 0, net_bn: "-237.00", sum_bn: "-11825.40", missing: 0 }))
    .toEqual({ value: "−237,0 tỷ", tone: "negative", sub: "Phiên 23/11 · 20 phiên −11.825 tỷ" });
});

it("draws the bars from a middle line on one scale, a missing session as no bar", async () => {
  const { barHeights } = await import("./brief-market");
  const bars = [{ date: "a", net_bn: "10.00" }, { date: "b", net_bn: "-5.00" }, { date: "c", net_bn: null }, { date: "d", net_bn: "0.00" }];
  expect(barHeights(bars, 20)).toEqual([{ y: 0, h: 10, tone: "positive" }, { y: 10, h: 5, tone: "negative" }, null, { y: 10, h: 0, tone: "" }]);
  expect(barHeights([{ date: "a", net_bn: "0.00" }], 20)).toEqual([{ y: 10, h: 0, tone: "" }]);  // all zero: no division by zero
});
