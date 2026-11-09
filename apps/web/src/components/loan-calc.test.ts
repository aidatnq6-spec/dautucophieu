import { describe, expect, it } from "vitest";
import { loanSchedule, parseAmount, paymentStep, savedByPrepaying, shareText } from "./loan-calc";

const BASE = { principal: 2_000_000_000, months: 300, promoMonths: 12, promoRate: 7.5, afterRate: 11, method: "declining" as const };

describe("loanSchedule, declining balance", () => {
  it("gives the first payment and total interest of a 2 tỷ, 25-year loan at 7,5% for a year then 11%", () => {
    const s = loanSchedule(BASE);
    expect(s.rows).toHaveLength(300);
    expect(Math.round(s.rows[0].payment)).toBe(19_166_667);
    expect(Math.round(s.interest)).toBe(2_690_450_000);
    expect(s.rows[299].closing).toBeCloseTo(0, 2);
    expect(s.rows[12].rate).toBe(11);
    expect(s.rows[11].rate).toBe(7.5);
  });
  it("scales to a 2,1 tỷ loan", () => {
    const s = loanSchedule({ ...BASE, principal: 2_100_000_000 });
    expect(Math.round(s.rows[0].payment)).toBe(20_125_000);
    expect(Math.round(s.interest)).toBe(2_824_972_500);
  });
});

describe("loanSchedule, equal monthly payments", () => {
  it("is level within a rate, repays the loan exactly, and is worked out anew when the rate changes", () => {
    const s = loanSchedule({ ...BASE, method: "annuity" });
    const r = 0.075 / 12;
    expect(s.rows[0].payment).toBeCloseTo((2e9 * r) / (1 - (1 + r) ** -300), 2);
    expect(s.rows[5].payment).toBeCloseTo(s.rows[0].payment, 2);
    expect(s.rows[12].payment).toBeGreaterThan(s.rows[11].payment);
    expect(s.rows[13].payment).toBeCloseTo(s.rows[12].payment, 2);
    expect(s.rows[299].closing).toBeCloseTo(0, 2);
    expect(s.rows.reduce((a, x) => a + x.principal, 0)).toBeCloseTo(2e9, 2);
  });
  it("handles a zero rate", () => {
    const s = loanSchedule({ principal: 1200, months: 12, promoMonths: 0, promoRate: 0, afterRate: 0, method: "annuity" });
    expect(s.rows[0].payment).toBe(100);
    expect(s.interest).toBe(0);
  });
});

describe("grace on principal", () => {
  it("charges interest only during the grace, then repays over the months left", () => {
    const s = loanSchedule({ principal: 1200, months: 12, promoMonths: 0, promoRate: 0, afterRate: 12, method: "declining", graceMonths: 2 });
    expect(s.rows[1].principal).toBe(0);
    expect(s.rows[1].payment).toBe(12);
    expect(s.rows[2].principal).toBe(120);
    expect(s.rows[11].closing).toBeCloseTo(0, 6);
    const a = loanSchedule({ ...BASE, method: "annuity", graceMonths: 6 });
    expect(a.rows[5].principal).toBe(0);
    expect(a.rows[299].closing).toBeCloseTo(0, 2);
  });
});

describe("repaying early", () => {
  const plan = { principal: 1200, months: 12, promoMonths: 0, promoRate: 0, afterRate: 12, method: "declining" as const };
  it("clears the balance at the end of the chosen month and charges the fee on what is cleared", () => {
    const s = loanSchedule({ ...plan, prepay: { month: 3, feePercent: 2 } });
    expect(s.rows).toHaveLength(3);
    expect(s.rows[2].closing).toBe(0);
    expect(s.rows[2].fee).toBeCloseTo(18, 8);  // 2% of the 900 left after the month's own instalment
    expect(s.rows[2].principal).toBeCloseTo(1000, 8);
    expect(s.fee).toBeCloseTo(18, 8);
    expect(s.total).toBeCloseTo(1200 + s.interest + 18, 8);
  });
  it("says how much interest is saved after the fee", () => {
    const full = loanSchedule(plan), early = loanSchedule({ ...plan, prepay: { month: 3, feePercent: 2 } });
    expect(savedByPrepaying(full, early)).toBeCloseTo(full.interest - early.interest - 18, 8);
  });
});

describe("the payment when the promotion ends", () => {
  it("compares the first month after it with the month before: 18.708.333 đ then 24.266.667 đ on 2 tỷ, 25 years, 7,5% then 11%", () => {
    const step = paymentStep(loanSchedule(BASE), 12)!;
    expect(step.period).toBe(13);
    expect(Math.round(step.first)).toBe(19_166_667);
    expect(Math.round(step.after)).toBe(24_266_667);
    expect(Math.round(step.rise)).toBe(5_558_333);
    expect(shareText(step.rise, step.after - step.rise)).toBe("29,7%");
  });
  it("waits for the principal to start when the grace outlasts the promotion", () => {
    const s = loanSchedule({ ...BASE, graceMonths: 18 });
    expect(paymentStep(s, 12, 18)!.period).toBe(19);
  });
  it("shows a fall as a negative rise", () => {
    expect(paymentStep(loanSchedule({ ...BASE, promoRate: 12, afterRate: 6 }), 12)!.rise).toBeLessThan(0);
  });
  it("is absent when there is no second rate to compare", () => {
    expect(paymentStep(loanSchedule({ ...BASE, promoMonths: 0 }), 0)).toBeNull();
    expect(paymentStep(loanSchedule({ ...BASE, afterRate: 7.5 }), 12)).toBeNull();
    expect(paymentStep(loanSchedule({ ...BASE, promoMonths: 300 }), 300)).toBeNull();
  });
  it("is absent when that month is the one the loan is cleared in, whose payment is not a monthly one", () => {
    expect(paymentStep(loanSchedule({ ...BASE, prepay: { month: 13, feePercent: 2 } }), 12)).toBeNull();
  });
});

it("gives a share of a total to one decimal, with a comma", () => {
  expect(shareText(2_000_000_000, 4_690_450_000)).toBe("42,6%");
  expect(shareText(2_690_450_000, 4_690_450_000)).toBe("57,4%");
});

describe("parseAmount", () => {
  it("reads a decimal in tỷ with either mark, and thousands in triệu", () => {
    expect(parseAmount("1.5", "ty")).toBe(1_500_000_000);  // the old page made this 15 tỷ
    expect(parseAmount("1,5", "ty")).toBe(1_500_000_000);
    expect(parseAmount("1.000", "trieu")).toBe(1_000_000_000);
    expect(parseAmount("750", "trieu")).toBe(750_000_000);
    expect(parseAmount("abc", "ty")).toBeNull();
    expect(parseAmount("-1", "ty")).toBeNull();
  });
});
