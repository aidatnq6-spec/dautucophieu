import { expect, it } from "vitest";
import { baseText, streakText } from "./brief-market";

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
