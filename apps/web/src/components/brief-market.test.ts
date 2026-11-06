import { expect, it } from "vitest";
import { baseText, recoveryHead, spreadText, streakText } from "./brief-market";

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
