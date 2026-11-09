import { describe, expect, it } from "vitest";
import { compact, growthPath, monthsToReach, niceTicks, reachText, scenarioRates, shortTy, spreadLabels, yearAt } from "./growth-path";

describe("growthPath", () => {
  it("compounds monthly with the contribution at each month's end, year by year, as the goal's own estimate does", () => {
    const p = growthPath({ capital: 200_000_000, monthly: 5_000_000, rate: 5, years: 20 });
    expect(p.paid).toHaveLength(21);
    expect(p.paid[0]).toBe(200_000_000);
    expect(p.paid[20]).toBe(1_400_000_000);
    expect(p.value[0]).toBe(200_000_000);
    let check = 200_000_000;
    for (let i = 0; i < 240; i++) check = check * (1 + 0.05 / 12) + 5_000_000;
    expect(p.value[20]).toBeCloseTo(check, 2);
  });
  it("at a zero rate is what was paid in", () => {
    expect(growthPath({ capital: 100, monthly: 10, rate: 0, years: 1 }).value[1]).toBe(220);
  });
  it("in today's money divides each year by the inflation to it", () => {
    const p = growthPath({ capital: 100, monthly: 0, rate: 0, years: 2, inflation: 10 });
    expect(p.real?.[2]).toBeCloseTo(100 / 1.21, 8);
    expect(growthPath({ capital: 100, monthly: 0, rate: 0, years: 2 }).real).toBeNull();
  });
});

describe("scenarioRates", () => {
  it("starts two points either side of the goal's assumed rate, never below zero", () => {
    expect(scenarioRates(6)).toEqual([4, 6, 8]);
    expect(scenarioRates(1)).toEqual([0, 1, 3]);
  });
});

describe("shortTy", () => {
  it("writes an axis figure in tỷ đồng", () => {
    expect(shortTy(1_500_000_000)).toBe("1,5 tỷ");
    expect(shortTy(0)).toBe("0");
  });
});


describe("growthPath with a yearly raise in the contribution", () => {
  it("raises the monthly amount each year after the first", () => {
    const p = growthPath({ capital: 0, monthly: 10, rate: 0, years: 2, raise: 10 });
    expect(p.value[1]).toBeCloseTo(120, 6);
    expect(p.value[2]).toBeCloseTo(252, 6);
    expect(p.paid[2]).toBeCloseTo(252, 6);
  });
  it("keeps the contribution level without one", () => {
    expect(growthPath({ capital: 0, monthly: 10, rate: 0, years: 2 }).paid[2]).toBe(240);
  });
});

describe("niceTicks", () => {
  it("gives round marks in at most five steps, reaching past the top", () => {
    expect(niceTicks(21_353_872_910)).toEqual([0, 5e9, 10e9, 15e9, 20e9, 25e9]);
    expect(niceTicks(6_000_000_000)).toEqual([0, 2e9, 4e9, 6e9]);
    expect(niceTicks(430_000_000)).toEqual([0, 100e6, 200e6, 300e6, 400e6, 500e6]);
  });
  it("still draws an axis with nothing on it", () => {
    expect(niceTicks(0)).toEqual([0, 1]);
  });
});

describe("compact", () => {
  it("writes tỷ with one decimal and smaller figures in triệu", () => {
    expect(compact(21_353_872_910)).toBe("21,4 tỷ");
    expect(compact(5_000_000_000)).toBe("5 tỷ");
    expect(compact(400_000_000)).toBe("400 tr");
    expect(compact(0)).toBe("0");
  });
});

describe("monthsToReach", () => {
  it("counts the months at the chart's own formula", () => {
    expect(monthsToReach({ capital: 0, monthly: 10, rate: 0, required: 120 })).toBe(12);
    expect(monthsToReach({ capital: 0, monthly: 10, rate: 0, required: 121 })).toBe(13);
  });
  it("is zero when already there", () => {
    expect(monthsToReach({ capital: 500, monthly: 0, rate: 0, required: 500 })).toBe(0);
  });
  it("follows a yearly raise", () => {
    expect(monthsToReach({ capital: 0, monthly: 10, rate: 0, raise: 10, required: 131 })).toBe(13);  // 120 after a year, then 11 a month
  });
  it("gives null when not reached in fifty years", () => {
    expect(monthsToReach({ capital: 0, monthly: 0, rate: 0, required: 1 })).toBeNull();
  });
  it("matches the yearly path", () => {
    const input = { capital: 200_000_000, monthly: 5_000_000, rate: 5 };
    const value = growthPath({ ...input, years: 10 }).value;
    const months = monthsToReach({ ...input, required: value[10] - 1 });
    expect(months).toBe(120);
  });
});

describe("reachText", () => {
  it("says when, in years and months", () => {
    expect(reachText(0)).toBe("Đã đạt vốn cần có");
    expect(reachText(120)).toBe("Đạt vốn cần có sau khoảng 10 năm");
    expect(reachText(125)).toBe("Đạt vốn cần có sau khoảng 10 năm 5 tháng");
    expect(reachText(7)).toBe("Đạt vốn cần có sau khoảng 7 tháng");
    expect(reachText(null)).toBe("Chưa đạt vốn cần có trong 50 năm");
  });
});

describe("spreadLabels", () => {
  it("leaves labels far apart where they are", () => {
    expect(spreadLabels([10, 50, 90], 14, 0, 100)).toEqual([10, 50, 90]);
  });
  it("pushes close labels apart, in the same order as given", () => {
    const out = spreadLabels([50, 40, 45], 14, 0, 100);
    const sorted = [...out].sort((a, b) => a - b);
    expect(sorted[1] - sorted[0]).toBeGreaterThanOrEqual(14);
    expect(sorted[2] - sorted[1]).toBeGreaterThanOrEqual(14);
    expect(out[1]).toBeLessThan(out[2]);
    expect(out[2]).toBeLessThan(out[0]);
  });
  it("stays inside the plot", () => {
    const out = spreadLabels([98, 99, 100], 14, 0, 100);
    expect(Math.max(...out)).toBeLessThanOrEqual(100);
    expect(Math.min(...out)).toBeGreaterThanOrEqual(0);
  });
});

describe("yearAt", () => {
  it("snaps the pointer to the nearest year inside the plot", () => {
    expect(yearAt(58, 58, 558, 20)).toBe(0);
    expect(yearAt(308, 58, 558, 20)).toBe(10);
    expect(yearAt(900, 58, 558, 20)).toBe(20);
    expect(yearAt(0, 58, 558, 20)).toBe(0);
  });
});

