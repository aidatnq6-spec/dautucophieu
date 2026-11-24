import { describe, expect, it } from "vitest";
import { backLine, byGivenBack, goalLine, peakLine, percentInput, type GoalStatus, type Row } from "./giveback-view";

const row: Row = { symbol: "FPT", since: "2027-01-05", reason: null, never_gained: false, sessions_since_peak: 2,
  peak: { gain: "2000000", ratio: "0.4000", on: "2027-01-06" }, now: { gain: "500000", ratio: "0.1000", on: "2027-01-08" },
  given_back: "1500000", share: "0.7500", days: [] };

const blank: GoalStatus = { enough: null, short: null, since: null, days: null, before_goal: null, last: null, last_before_goal: null };

describe("giveback", () => {
  it("states the peak, or why there is none", () => {
    expect(peakLine(row)).toBe("2.000.000 đ (+40,0%) ngày 06/01/2027");
    expect(peakLine({ ...row, peak: null, never_gained: true })).toBe("Chưa từng có lãi trong đợt nắm này");
    expect(peakLine({ ...row, peak: null, reason: "Chưa có giá đã lưu của mã" })).toBe("Chưa có giá đã lưu của mã");
  });
  it("says what went back and how long ago the peak was", () => {
    expect(backLine(row)).toBe("1.500.000 đ, bằng 75,0% lãi cao nhất · đỉnh lãi cách 2 phiên");
    expect(backLine({ ...row, given_back: "0", share: "0.0000", sessions_since_peak: 0 })).toBe("Chưa trả lại: hôm nay là lãi cao nhất");
    expect(backLine({ ...row, given_back: null, share: null })).toBe("—");
  });
  it("puts the largest amount given back first and rows without one last", () => {
    const small = { ...row, symbol: "HPG", given_back: "10" }, none = { ...row, symbol: "VCB", given_back: null };
    expect([none, small, row].sort(byGivenBack).map((r) => r.symbol)).toEqual(["FPT", "HPG", "VCB"]);
  });
  it("reads a percent above 100 for the minimum gain", () => {
    expect(percentInput("150")).toBe("1.5");
    expect(percentInput("30,5")).toBe("0.305");
    expect(percentInput("")).toBeNull();
    expect(percentInput("abc")).toBeNull();
  });
  it("tells a goal's state in words", () => {
    expect(goalLine({ ...blank, enough: true, since: "2027-01-06", days: 2, before_goal: false })).toBe("Đã đủ từ 06/01/2027 (2 ngày)");
    expect(goalLine({ ...blank, enough: true, since: "2027-01-06", days: 0, before_goal: true })).toBe("Đã đủ từ 06/01/2027, trước khi bạn đặt mục tiêu");
    expect(goalLine({ ...blank, enough: false, short: "1000000", last: { from: "2027-01-06", to: "2027-01-07", excess: "500000" }, last_before_goal: true }))
      .toBe("Còn thiếu 1.000.000 đ · từng đủ từ 06/01/2027 đến 07/01/2027, vượt tối đa 500.000 đ (trước khi bạn đặt mục tiêu)");
    expect(goalLine({ ...blank, enough: false, short: "1000000" })).toBe("Còn thiếu 1.000.000 đ");
    expect(goalLine(blank)).toBe("Chưa tính được: danh mục thiếu giá đã lưu");
  });
});
