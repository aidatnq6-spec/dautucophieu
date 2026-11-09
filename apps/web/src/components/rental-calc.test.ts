import { describe, expect, it } from "vitest";
import { rentalCompare } from "./rental-calc";

const BASE = { price: 2_000_000_000, own: 2_000_000_000, upfront: 0, rent: 5_000_000, running: 1_000_000, loanRate: 12, termYears: 10, method: "declining" as const, depositRate: 6, years: 1 };

describe("rentalCompare", () => {
  it("gives the yield on the price, before and after running costs", () => {
    const r = rentalCompare(BASE);
    expect(r.grossYield).toBeCloseTo(0.03, 8);
    expect(r.netYield).toBeCloseTo(0.024, 8);
  });
  it("without a loan, sets the deposit against the price the home must reach, counting the rent kept on deposit", () => {
    const r = rentalCompare(BASE);
    const grow = 1.005 ** 12;
    expect(r.loan).toBe(0);
    expect(r.keep).toBeCloseTo(2_000_000_000 * grow, 0);
    expect(r.flowsValue).toBeCloseTo((4_000_000 * (grow - 1)) / 0.005, 0);
    expect(r.neededPrice).toBeCloseTo(r.keep - r.flowsValue, 0);
    expect(r.neededGrowth).toBeCloseTo(r.neededPrice / 2_000_000_000 - 1, 8);
  });
  it("with a loan, takes the monthly payment from the cash flow and adds the debt left to the price needed", () => {
    const r = rentalCompare({ ...BASE, own: 1_000_000_000 });
    expect(r.loan).toBe(1_000_000_000);
    expect(r.firstFlow).toBeCloseTo(4_000_000 - (1_000_000_000 / 120 + 10_000_000), 0);  // the shortfall is what the owner tops up each month
    expect(r.balance).toBeCloseTo(900_000_000, 0);
    expect(r.neededPrice).toBeCloseTo(r.keep - r.flowsValue + 900_000_000, 0);
  });
  it("buying costs are financed too", () => {
    expect(rentalCompare({ ...BASE, upfront: 100_000_000 }).loan).toBe(100_000_000);
  });
  it("a loan paid off inside the holding period costs nothing afterwards", () => {
    const r = rentalCompare({ ...BASE, own: 1_000_000_000, termYears: 1, years: 2 });
    expect(r.balance).toBe(0);
  });
  it("gives no growth when the rent alone already beats the deposit", () => {
    const r = rentalCompare({ ...BASE, price: 100, own: 100, rent: 1_000_000, running: 0, years: 5 });
    expect(r.neededGrowth).toBeNull();
  });
});
