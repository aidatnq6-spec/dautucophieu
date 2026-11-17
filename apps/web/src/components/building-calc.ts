import { loanSchedule, type Method } from "./loan-calc";

/** One season of the year: how many months, the rent of a room a month, and the share of rooms let (%). */
export type Season = { months: number; rent: number; occupancy: number };
export type Equipment = { name: string; count: number; price: number; lifeYears: number };
export type BuildingInput = {
  rooms: number; seasons: Season[]; peakRent: number | null;
  /** shares of revenue, in %: broker and OTA commission (otaShare: the part of revenue sold through OTAs), VAT, personal income tax, other */
  brokerPct: number; otaPct: number; otaShare: number; vatPct: number; pitPct: number; otherPct: number;
  fixed: { cleaning: number; common: number; staff: number; internet: number; insurance: number; other: number };
  equipment: Equipment[]; pccc: { cost: number; years: number }; reservePct: number;
  /** holdYears and depositRate (%/year): the building held that long against the own money kept on deposit */
  buy?: { price: number; buyCosts: number; renovation: number; own: number; loanRate: number; termYears: number; method: Method;
    holdYears?: number; depositRate?: number };
  lease?: { rent: number; deposit: number; setup: number; months: number };
};
export type Costs = { commission: number; tax: number; other: number; reserve: number; fixed: number; equipment: number; pccc: number; total: number };
export type BuildingPlan = {
  monthsCheck: number; revenueYear: number; revenueMonth: number; potentialYear: number; vacancyLossYear: number; vacancyShare: number;
  peakOverstates: number | null; costs: Costs; costShare: number; noiMonth: number;
  /** the share of rooms let, all year at the rents entered, where operating profit is nil (Infinity when no occupancy reaches it) */
  breakevenOccupancy: number;
  buy: { loan: number; invested: number; loanPaymentMonth: number; cashMonth: number; netYield: number; cashOnCash: number | null;
    paybackYears: number | null; breakevenOccupancy: number;
    /** the deposit the own money would grow to, the monthly cash carried on the same deposit, the loan left, and the price the
     * building must reach for holding it to match the deposit (the same arithmetic as the one-flat check, rental-calc) */
    hold: { years: number; keep: number; flowsValue: number; balance: number; neededPrice: number; neededGrowth: number | null } | null } | null;
  lease: { breakevenRevenue: number; multiple: number; breakevenOccupancy: number; profitMonth: number; contractProfit: number;
    setupPaybackMonths: number | null } | null;
};

/** Profit of a building let by the room (Tính lợi nhuận tòa nhà): revenue by season, the costs that follow revenue, the fixed ones and the
 * hidden ones (equipment worn out, the fire-safety papers), then either buying the building with a loan or leasing it whole to run it.
 * Every figure is the owner's own; nothing is filled in. */
export function buildingPlan(i: BuildingInput): BuildingPlan {
  const monthsCheck = i.seasons.reduce((s, x) => s + x.months, 0);
  const revenueYear = i.seasons.reduce((s, x) => s + i.rooms * x.months * x.rent * (x.occupancy / 100), 0);
  const potentialYear = i.seasons.reduce((s, x) => s + i.rooms * x.months * x.rent, 0);
  const months = monthsCheck || 12;
  const revenueMonth = revenueYear / months, potentialMonth = potentialYear / months;
  const pct = {
    commission: ((100 - i.otaShare) / 100) * (i.brokerPct / 100) + (i.otaShare / 100) * (i.otaPct / 100),
    tax: (i.vatPct + i.pitPct) / 100, other: i.otherPct / 100, reserve: i.reservePct / 100,
  };
  const share = pct.commission + pct.tax + pct.other + pct.reserve;
  const fixed = Object.values(i.fixed).reduce((s, v) => s + v, 0);
  const equipment = i.equipment.reduce((s, e) => s + (e.lifeYears > 0 ? (e.count * e.price) / (e.lifeYears * 12) : 0), 0);
  const pccc = i.pccc.years > 0 ? i.pccc.cost / (i.pccc.years * 12) : 0;
  const fixedish = fixed + equipment + pccc;   // costs that do not follow revenue
  const costs: Costs = { commission: revenueMonth * pct.commission, tax: revenueMonth * pct.tax, other: revenueMonth * pct.other,
    reserve: revenueMonth * pct.reserve, fixed, equipment, pccc, total: revenueMonth * share + fixedish };
  const noiMonth = revenueMonth - costs.total;
  const needed = (extra: number) => (share < 1 ? (fixedish + extra) / (1 - share) : Infinity);

  let buy: BuildingPlan["buy"] = null;
  if (i.buy) {
    const b = i.buy, invested = b.price + b.buyCosts + b.renovation, loan = Math.max(invested - b.own, 0);
    const rows = loan > 0 && b.termYears > 0
      ? loanSchedule({ principal: loan, months: b.termYears * 12, promoMonths: 0, promoRate: b.loanRate, afterRate: b.loanRate, method: b.method }).rows : [];
    const firstYear = rows.slice(0, 12);
    const loanPaymentMonth = firstYear.length ? firstYear.reduce((s, r) => s + r.payment, 0) / firstYear.length : 0;
    const cashMonth = noiMonth - loanPaymentMonth;
    let hold: NonNullable<BuildingPlan["buy"]>["hold"] = null;
    if (b.holdYears && b.holdYears > 0 && b.depositRate !== undefined && b.depositRate >= 0) {
      const months = Math.round(b.holdYears * 12), monthly = b.depositRate / 100 / 12;
      let flowsValue = 0;
      for (let m = 1; m <= months; m++) flowsValue = flowsValue * (1 + monthly) + noiMonth - (rows[m - 1]?.payment ?? 0);
      const keep = b.own * (1 + monthly) ** months, balance = rows[months - 1]?.closing ?? 0, neededPrice = keep - flowsValue + balance;
      hold = { years: b.holdYears, keep, flowsValue, balance, neededPrice,
        neededGrowth: neededPrice > 0 && b.price > 0 ? (neededPrice / b.price) ** (1 / b.holdYears) - 1 : null };
    }
    buy = { loan, invested, loanPaymentMonth, cashMonth, netYield: invested > 0 ? (noiMonth * 12) / invested : 0,
      cashOnCash: b.own > 0 ? (cashMonth * 12) / b.own : null, paybackYears: cashMonth > 0 && b.own > 0 ? b.own / (cashMonth * 12) : null,
      breakevenOccupancy: potentialMonth > 0 ? needed(loanPaymentMonth) / potentialMonth : Infinity, hold };
  }
  let lease: BuildingPlan["lease"] = null;
  if (i.lease) {
    const l = i.lease, breakevenRevenue = needed(l.rent), profitMonth = noiMonth - l.rent;
    lease = { breakevenRevenue, multiple: l.rent > 0 ? breakevenRevenue / l.rent : Infinity,
      breakevenOccupancy: potentialMonth > 0 ? breakevenRevenue / potentialMonth : Infinity, profitMonth,
      contractProfit: profitMonth * l.months - l.setup, setupPaybackMonths: profitMonth > 0 ? l.setup / profitMonth : null };
  }
  return { monthsCheck, revenueYear, revenueMonth, potentialYear, vacancyLossYear: potentialYear - revenueYear,
    vacancyShare: potentialYear > 0 ? (potentialYear - revenueYear) / potentialYear : 0,
    peakOverstates: i.peakRent && revenueYear > 0 ? (i.peakRent * 12 * i.rooms) / revenueYear - 1 : null,
    costs, costShare: revenueMonth > 0 ? costs.total / revenueMonth : 0, noiMonth,
    breakevenOccupancy: potentialMonth > 0 ? needed(0) / potentialMonth : Infinity, buy, lease };
}

/** A scenario: occupancy moved by points (kept within 0–100%) and rent by a share (%), in every season. */
export function scenario(i: BuildingInput, occupancyPoints: number, rentPct: number): BuildingPlan {
  return buildingPlan({ ...i, seasons: i.seasons.map((s) => ({ ...s, occupancy: Math.min(100, Math.max(0, s.occupancy + occupancyPoints)),
    rent: s.rent * (1 + rentPct / 100) })) });
}

export type Measure = "noi" | "buy" | "lease";
const pick = (p: BuildingPlan, m: Measure): number | null => (m === "noi" ? p.noiMonth : m === "buy" ? p.buy?.cashMonth ?? null : p.lease?.profitMonth ?? null);

/** Rows: one occupancy for the whole year (%); columns: rent moved by a share (%); each cell the chosen monthly result. */
export function sensitivity(i: BuildingInput, occupancies: number[], rentPcts: number[], measure: Measure): (number | null)[][] {
  return occupancies.map((o) => rentPcts.map((r) => pick(buildingPlan({ ...i, seasons: i.seasons.map((s) => ({ ...s, occupancy: o,
    rent: s.rent * (1 + r / 100) })) }), measure)));
}

export function measureOf(p: BuildingPlan, m: Measure): number | null {
  return pick(p, m);
}
