/** Tính khoản vay: a month-by-month estimate. Interest each month is the balance × the yearly rate ÷ 12; banks usually count actual days, so theirs differs slightly. */

export type Method = "declining" | "annuity";
export type LoanInput = { principal: number; months: number; promoMonths: number; promoRate: number; afterRate: number; method: Method; graceMonths?: number;
  prepay?: { month: number; feePercent: number } | null };
export type LoanRow = { period: number; opening: number; principal: number; interest: number; fee: number; payment: number; closing: number; rate: number };
export type Loan = { rows: LoanRow[]; interest: number; fee: number; total: number };

/** In the grace, interest only. After it: equal principal, or a level payment worked out anew whenever the rate changes. */
export function loanSchedule(input: LoanInput): Loan {
  const { principal, months, promoMonths, promoRate, afterRate, method, prepay } = input;
  const grace = Math.max(input.graceMonths ?? 0, 0);
  const instalment = principal / (months - grace);
  const rows: LoanRow[] = [];
  let balance = principal, level = 0, levelRate: number | null = null;
  for (let period = 1; period <= months; period++) {
    const rate = period <= promoMonths ? promoRate : afterRate;
    const monthly = rate / 100 / 12;
    const interest = balance * monthly;
    let paid = 0;
    if (period > grace) {
      if (method === "declining") paid = instalment;
      else {
        if (rate !== levelRate) {
          const left = months - period + 1;
          level = monthly === 0 ? balance / left : (balance * monthly) / (1 - (1 + monthly) ** -left);
          levelRate = rate;
        }
        paid = level - interest;
      }
      if (period === months) paid = balance;  // the last instalment clears what rounding left
    }
    let fee = 0, closing = balance - paid;
    const last = prepay && prepay.month === period && period < months;
    if (last) {
      fee = closing * (prepay.feePercent / 100);
      paid += closing;
      closing = 0;
    }
    rows.push({ period, opening: balance, principal: paid, interest, fee, payment: paid + interest + fee, closing, rate });
    balance = closing;
    if (last) break;
  }
  const interest = rows.reduce((a, r) => a + r.interest, 0), fee = rows.reduce((a, r) => a + r.fee, 0);
  return { rows, interest, fee, total: principal + interest + fee };
}

/** The first monthly payment once the rate has changed and the principal has started, against the month before; null when no such comparison exists:
 * no promotion, the same rate after it, or that month being the loan's last (when repaying early, its payment is the whole balance). */
export function paymentStep(loan: Loan, promoMonths: number, graceMonths = 0): { first: number; after: number; period: number; rise: number } | null {
  if (promoMonths <= 0) return null;
  const index = Math.max(promoMonths, graceMonths);
  const after = loan.rows[index];
  if (!after || index === loan.rows.length - 1 || after.rate === loan.rows[promoMonths - 1].rate) return null;
  return { first: loan.rows[0].payment, after: after.payment, period: after.period, rise: after.payment - loan.rows[index - 1].payment };
}

export type StressRow = { rate: number; peak: number; peakPeriod: number; times: number | null; interestTimes: number | null; interest: number };

/** The loan at each rate after the promotion, repaid to term. times: the highest payment over the planned first payment. interestTimes: the
 * first month's interest after the promotion over the last month's within it; null without a promotion or a month after it. */
export function stressLoan(input: LoanInput, rates: number[]): StressRow[] {
  const first = loanSchedule({ ...input, prepay: null }).rows[0].payment;
  return rates.map((rate) => {
    const s = loanSchedule({ ...input, afterRate: rate, prepay: null });
    const top = s.rows.reduce((a, r) => (r.payment > a.payment ? r : a));
    const before = s.rows[input.promoMonths - 1], after = s.rows[input.promoMonths];
    return { rate, peak: top.payment, peakPeriod: top.period, times: first > 0 ? top.payment / first : null,
      interestTimes: before && after && before.interest > 0 ? after.interest / before.interest : null, interest: s.interest };
  });
}

export type Cashflow = { firstRatio: number; peakRatio: number; peak: number; peakPeriod: number; firstLeft: number | null; worstLeft: number | null; firstNegative: number | null;
  reserve: { covered: number | null; runsOut: number | null } | null };

/** What a loan repaid to term leaves of a month's income. Anything resting on a figure not given is null. The reserve is drawn from the first short
 * month on, one month's shortfall at a time; a later month's surplus is not added back. covered and runsOut are null when it lasts through every short month. */
export function cashflowAfterLoan(loan: Loan, money: { income: number; expense: number | null; reserve: number | null }): Cashflow {
  const { income, expense, reserve } = money;
  const top = loan.rows.reduce((a, r) => (r.payment > a.payment ? r : a));
  const base = { firstRatio: loan.rows[0].payment / income, peakRatio: top.payment / income, peak: top.payment, peakPeriod: top.period };
  if (expense === null) return { ...base, firstLeft: null, worstLeft: null, firstNegative: null, reserve: null };
  const left = loan.rows.map((r) => income - expense - r.payment);
  const firstIndex = left.findIndex((v) => v < 0);
  let result: Cashflow["reserve"] = null;
  if (reserve !== null) {
    result = { covered: null, runsOut: null };
    let balance = reserve, covered = 0;
    for (let i = Math.max(firstIndex, 0); firstIndex >= 0 && i < left.length; i++) {
      if (left[i] >= 0) continue;
      if (balance + left[i] < 0) { result = { covered, runsOut: loan.rows[i].period }; break; }
      balance += left[i];
      covered++;
    }
  }
  return { ...base, firstLeft: left[0], worstLeft: Math.min(...left), firstNegative: firstIndex >= 0 ? loan.rows[firstIndex].period : null, reserve: result };
}

export const shareText = (part: number, whole: number) => `${((part / whole) * 100).toFixed(1).replace(".", ",")}%`;

export const savedByPrepaying = (full: Loan, early: Loan) => full.interest - early.interest - early.fee;

/** An amount typed in tỷ (1.5 and 1,5 are both one and a half) or in triệu (1.000 is a thousand); null when unreadable or negative. */
export function parseAmount(raw: string, unit: "ty" | "trieu"): number | null {
  let t = raw.trim().replace(/\s/g, "");
  if (unit === "trieu" && /^\d{1,3}(\.\d{3})+(,\d+)?$/.test(t)) t = t.replace(/\./g, "");
  t = t.replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(t)) return null;
  return Number(t) * (unit === "ty" ? 1e9 : 1e6);
}
