import { describe, expect, it } from "vitest";
import { buildingPlan, type BuildingInput } from "./building-calc";

// A made-up building: 10 rooms; 5 high months at 10m a room 90% full, 7 low months at 8m 70% full.
const BASE: BuildingInput = {
  rooms: 10, seasons: [{ months: 5, rent: 10_000_000, occupancy: 90 }, { months: 7, rent: 8_000_000, occupancy: 70 }], peakRent: 12_000_000,
  brokerPct: 10, otaPct: 15, otaShare: 40, vatPct: 5, pitPct: 5, otherPct: 0,
  fixed: { cleaning: 8_000_000, common: 3_000_000, staff: 10_000_000, internet: 1_000_000, insurance: 1_000_000, other: 0 },
  equipment: [{ name: "Điều hòa", count: 10, price: 12_000_000, lifeYears: 8 }], pccc: { cost: 60_000_000, years: 5 }, reservePct: 2,
};

describe("revenue", () => {
  it("averages the seasons and says how far the peak price times twelve overstates it", () => {
    const r = buildingPlan(BASE);
    // 10 × (5 × 10m × 0.9 + 7 × 8m × 0.7) = 10 × (45m + 39.2m) = 842m a year
    expect(r.revenueYear).toBe(842_000_000);
    expect(Math.round(r.revenueMonth)).toBe(70_166_667);
    // full rooms all year: 10 × (5 × 10m + 7 × 8m) = 1,060m; empty rooms cost 218m, 20.57% of it
    expect(r.vacancyLossYear).toBe(218_000_000);
    expect(r.vacancyShare).toBeCloseTo(0.2057, 4);
    // the peak monthly price × 12 for every room: 1,440m against 842m → 71.0% more
    expect(r.peakOverstates).toBeCloseTo(1440 / 842 - 1, 6);
    expect(r.monthsCheck).toBe(12);
  });
});

describe("costs", () => {
  it("splits the share of revenue costs, the fixed ones and the hidden ones", () => {
    const r = buildingPlan(BASE);
    const m = 842_000_000 / 12;
    // commission: 60% through brokers at 10%, 40% through OTAs at 15% → 12% of revenue
    expect(r.costs.commission).toBeCloseTo(m * 0.12, 4);
    expect(r.costs.tax).toBeCloseTo(m * 0.10, 4);
    expect(r.costs.reserve).toBeCloseTo(m * 0.02, 4);
    expect(r.costs.fixed).toBe(23_000_000);
    expect(r.costs.equipment).toBeCloseTo((10 * 12_000_000) / (8 * 12), 6);   // 1.25m a month
    expect(r.costs.pccc).toBe(1_000_000);
    expect(r.costShare).toBeCloseTo(r.costs.total / m, 10);
    expect(r.noiMonth).toBeCloseTo(m - r.costs.total, 6);
  });
});

describe("buying the building", () => {
  it("gives the cash after the loan, the return on own money and the payback", () => {
    const r = buildingPlan({ ...BASE, buy: { price: 5_000_000_000, buyCosts: 200_000_000, renovation: 300_000_000, own: 2_500_000_000,
      loanRate: 10, termYears: 10, method: "annuity" } });
    const b = r.buy!;
    expect(b.loan).toBe(3_000_000_000);
    expect(b.invested).toBe(5_500_000_000);
    expect(b.netYield).toBeCloseTo((r.noiMonth * 12) / 5_500_000_000, 10);
    expect(b.cashMonth).toBeCloseTo(r.noiMonth - b.loanPaymentMonth, 6);
    expect(b.cashOnCash).toBeCloseTo((b.cashMonth * 12) / 2_500_000_000, 10);
    expect(b.loanPaymentMonth).toBeGreaterThan(39_000_000);   // 3bn over 10 years at 10%: about 39.6m a month
    expect(b.breakevenOccupancy).toBeGreaterThan(0);
  });
});

describe("leasing the whole building to run it", () => {
  it("gives the revenue that breaks even, its multiple of the lease and the lowest occupancy that covers it", () => {
    const r = buildingPlan({ ...BASE, lease: { rent: 20_000_000, deposit: 90_000_000, setup: 240_000_000, months: 36 } });
    const l = r.lease!;
    const pct = 0.12 + 0.10 + 0.02, fixedish = 23_000_000 + 1_250_000 + 1_000_000;
    expect(l.breakevenRevenue).toBeCloseTo((fixedish + 20_000_000) / (1 - pct), 4);
    expect(l.multiple).toBeCloseTo(l.breakevenRevenue / 20_000_000, 10);
    // full rooms bring 1,060m / 12 a month
    expect(l.breakevenOccupancy).toBeCloseTo(l.breakevenRevenue / (1_060_000_000 / 12), 10);
    expect(l.profitMonth).toBeCloseTo(r.noiMonth - 20_000_000, 6);
    expect(l.contractProfit).toBeCloseTo(l.profitMonth * 36 - 240_000_000, 4);
    expect(l.setupPaybackMonths).toBeCloseTo(240_000_000 / l.profitMonth, 6);
  });
  it("says no payback when the lease loses money", () => {
    const l = buildingPlan({ ...BASE, lease: { rent: 80_000_000, deposit: 0, setup: 100_000_000, months: 24 } }).lease!;
    expect(l.profitMonth).toBeLessThan(0);
    expect(l.setupPaybackMonths).toBeNull();
  });
});

describe("scenarios and sensitivity", () => {
  it("moves occupancy by points and rent by a share, within 0–100%", async () => {
    const { scenario } = await import("./building-calc");
    const bad = scenario(BASE, -15, -10);
    // 10 × (5 × 9m × 0.75 + 7 × 7.2m × 0.55) = 10 × (33.75m + 27.72m) = 614.7m a year
    expect(Math.round(bad.revenueYear)).toBe(614_700_000);
    expect(scenario(BASE, 50, 0).revenueYear).toBe(10 * (5 * 10_000_000 + 7 * 8_000_000));  // capped at full
  });
  it("tabulates the chosen result over occupancy levels for the whole year and rent changes", async () => {
    const { sensitivity } = await import("./building-calc");
    const t = sensitivity({ ...BASE, lease: { rent: 20_000_000, deposit: 0, setup: 0, months: 12 } }, [50, 100], [-10, 0], "lease");
    expect(t.length).toBe(2);
    expect(t[1][1]).toBeCloseTo(buildingPlan({ ...BASE, seasons: BASE.seasons.map((s) => ({ ...s, occupancy: 100 })),
      lease: { rent: 20_000_000, deposit: 0, setup: 0, months: 12 } }).lease!.profitMonth, 6);
    expect(t[0][0]!).toBeLessThan(t[1][1]!);
    expect(sensitivity(BASE, [80], [0], "buy")).toEqual([[null]]);  // no purchase entered: nothing to show
  });
});

describe("the occupancy that breaks even with the rents as entered", () => {
  it("is where operating profit is zero, before any loan or lease", () => {
    const r = buildingPlan(BASE);
    const share = 0.12 + 0.10 + 0.02, fixedish = 23_000_000 + 1_250_000 + 1_000_000;
    expect(r.breakevenOccupancy).toBeCloseTo(fixedish / (1 - share) / (1_060_000_000 / 12), 10);
    // checked: at that occupancy all year the operating profit is nil
    const at = buildingPlan({ ...BASE, seasons: BASE.seasons.map((s) => ({ ...s, occupancy: r.breakevenOccupancy * 100 })) });
    expect(Math.abs(at.noiMonth)).toBeLessThan(1);
  });
});

describe("holding the building against keeping the money on deposit", () => {
  it("gives the same price to reach as the one-flat check for one fully let flat", async () => {
    const { rentalCompare } = await import("./rental-calc");
    const one: BuildingInput = { rooms: 1, seasons: [{ months: 12, rent: 12_000_000, occupancy: 100 }], peakRent: null, brokerPct: 0, otaPct: 0, otaShare: 0,
      vatPct: 0, pitPct: 0, otherPct: 0, reservePct: 0, fixed: { cleaning: 0, common: 0, staff: 0, internet: 0, insurance: 0, other: 2_000_000 }, equipment: [],
      pccc: { cost: 0, years: 0 }, buy: { price: 3_000_000_000, buyCosts: 100_000_000, renovation: 0, own: 1_600_000_000, loanRate: 9, termYears: 15,
        method: "annuity", holdYears: 10, depositRate: 6 } };
    const hold = buildingPlan(one).buy!.hold!;
    const flat = rentalCompare({ price: 3_000_000_000, own: 1_600_000_000, upfront: 100_000_000, rent: 12_000_000, running: 2_000_000, loanRate: 9,
      termYears: 15, method: "annuity", depositRate: 6, years: 10 });
    expect(hold.neededPrice).toBeCloseTo(flat.neededPrice, 0);
    expect(hold.neededGrowth!).toBeCloseTo(flat.neededGrowth!, 10);
    expect(hold.keep).toBeCloseTo(flat.keep, 0);
  });
  it("is left out until the years and the deposit rate are both given", () => {
    const b = buildingPlan({ ...BASE, buy: { price: 5e9, buyCosts: 0, renovation: 0, own: 5e9, loanRate: 0, termYears: 0, method: "annuity" } }).buy!;
    expect(b.hold).toBeNull();
  });
});

describe("a loan with an offer rate first", () => {
  it("pays less in the offer year and shows what the cash and breakeven become after it", async () => {
    const { loanSchedule } = await import("./loan-calc");
    const buy = { price: 5_000_000_000, buyCosts: 0, renovation: 0, own: 2_000_000_000, loanRate: 10, termYears: 20, method: "annuity" as const };
    const plain = buildingPlan({ ...BASE, buy }).buy!;
    const offer = buildingPlan({ ...BASE, buy: { ...buy, promoRate: 6, promoMonths: 12 } }).buy!;
    const rows = loanSchedule({ principal: 3e9, months: 240, promoMonths: 12, promoRate: 6, afterRate: 10, method: "annuity" }).rows;
    expect(offer.loanPaymentMonth).toBeCloseTo(rows.slice(0, 12).reduce((s, r) => s + r.payment, 0) / 12, 6);
    expect(offer.loanPaymentMonth).toBeLessThan(plain.loanPaymentMonth);
    expect(offer.afterOffer!.month).toBe(13);
    expect(offer.afterOffer!.payment).toBeCloseTo(rows[12].payment, 6);
    expect(offer.afterOffer!.cashMonth).toBeCloseTo(offer.cashMonth + offer.loanPaymentMonth - rows[12].payment, 6);
    expect(offer.afterOffer!.breakevenOccupancy).toBeGreaterThan(offer.breakevenOccupancy);
    expect(plain.afterOffer).toBeNull();
  });
});
