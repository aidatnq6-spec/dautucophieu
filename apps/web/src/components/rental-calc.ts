import { loanSchedule, type Method } from "./loan-calc";

export type RentalInput = { price: number; own: number; upfront: number; rent: number; running: number; loanRate: number; termYears: number; method: Method; depositRate: number; years: number };
export type Rental = { loan: number; grossYield: number; netYield: number; firstFlow: number; keep: number; flowsValue: number; balance: number; neededPrice: number; neededGrowth: number | null };

/** Buying to let against keeping the own money on deposit, over the same years. Each month's difference (rent less costs and the loan payment) goes to or comes out of
 * the deposit, so both sides spend the same. Rent, costs and rates stay as typed; the price the home must reach is what comes out, never a forecast of it. */
export function rentalCompare(i: RentalInput): Rental {
  const loan = Math.max(i.price + i.upfront - i.own, 0);
  const months = i.years * 12, monthly = i.depositRate / 100 / 12;
  const rows = loan > 0 ? loanSchedule({ principal: loan, months: i.termYears * 12, promoMonths: 0, promoRate: i.loanRate, afterRate: i.loanRate, method: i.method }).rows : [];
  const income = i.rent - i.running;
  let flowsValue = 0;
  for (let m = 1; m <= months; m++) flowsValue = flowsValue * (1 + monthly) + income - (rows[m - 1]?.payment ?? 0);
  const keep = i.own * (1 + monthly) ** months;
  const balance = rows[months - 1]?.closing ?? 0;
  const neededPrice = keep - flowsValue + balance;
  return { loan, grossYield: (i.rent * 12) / i.price, netYield: (income * 12) / i.price, firstFlow: income - (rows[0]?.payment ?? 0), keep, flowsValue, balance, neededPrice,
    neededGrowth: neededPrice > 0 ? (neededPrice / i.price) ** (1 / i.years) - 1 : null };
}
