import { describe, expect, it } from "vitest";
import { parseAmount } from "./loan-calc";
import { prefillFields } from "./loan-tool";

describe("prefillFields", () => {
  it("puts a building's loan into the loan tab's boxes: one rate for the whole term, no offer, no grace", () => {
    const f = prefillFields({ principal: 2_537_500_000, rate: 9.5, years: 15, method: "annuity" });
    expect(f).toEqual({ mode: "loan", loan: "2537,5", loanUnit: "trieu", term: "15", termUnit: "year", promoRate: "9,5", afterRate: "9,5", promo: "0",
      promoUnit: "year", method: "annuity", grace: "0", prepayOn: false });
    expect(parseAmount(f.loan, f.loanUnit)).toBe(2_537_500_000);
  });
});

describe("prefillFields with an offer", () => {
  it("carries the offer rate and months over, the loan rate after them", () => {
    const f = prefillFields({ principal: 3e9, rate: 10, years: 20, method: "annuity", promoRate: 6, promoMonths: 12 });
    expect([f.promoRate, f.promo, f.promoUnit, f.afterRate]).toEqual(["6", "12", "month", "10"]);
  });
});
