/** V7 Chi phí hoán đổi ngoại tệ: the forward premium of a VND/USD swap, annualised over its tenor in months (simple, no compounding),
 * and the cost of VND it implies — the USD rate plus that premium (covered interest parity). Percent figures, per year. */
export function swapCost(i: { spot: number; forward: number; months: number; usdRate: number | null }):
  { premium: number; annual: number; vnd: number | null } | null {
  if (!(i.spot > 0) || !(i.forward > 0) || !(i.months > 0)) return null;
  const premium = (i.forward / i.spot - 1) * 100;
  const annual = premium * 12 / i.months;
  return { premium, annual, vnd: i.usdRate === null || !Number.isFinite(i.usdRate) ? null : i.usdRate + annual };
}

/** An exchange rate as typed in Vietnamese: dots and spaces group thousands, a comma marks decimals. */
export const parseFx = (raw: string) => (raw.trim() ? Number(raw.replace(/[.\s]/g, "").replace(",", ".")) : NaN);

/** A rate in percent: either mark is a decimal; empty is no figure. */
export const parseRate = (raw: string): number | null => {
  const v = raw.trim().replace(",", ".");
  return v && Number.isFinite(Number(v)) ? Number(v) : null;
};

/** The spread line in a width × height box, zero kept inside the range so the eye sees when VND pays less than USD. */
export function spreadPath(points: { spread: string }[], width: number, height: number): { line: string; zero: number } {
  const vals = points.map((p) => Number(p.spread));
  const hi = Math.max(0, ...vals), lo = Math.min(0, ...vals), span = hi - lo || 1;
  const y = (v: number) => Math.round(((hi - v) / span) * height * 100) / 100;
  const x = (i: number) => (vals.length > 1 ? Math.round((i / (vals.length - 1)) * width * 100) / 100 : 0);
  return { line: vals.map((v, i) => `${x(i)},${y(v)}`).join(" "), zero: y(0) };
}
