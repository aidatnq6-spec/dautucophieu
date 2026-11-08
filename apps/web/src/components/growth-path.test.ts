import { describe, expect, it } from "vitest";
import { growthPath, scenarioRates, shortTy } from "./growth-path";

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
