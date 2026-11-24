import { percentInput } from "./giveback-view";

/** Ngưỡng nhắc theo giỏ chiến lược: a basket's own Kế hoạch sụt giảm and Lãi đã trả lại levels, the common level, or no reminder. */
export type Mode = "default" | "custom" | "off";
export type DrawdownRule = { mode: Mode; threshold?: string | null };
export type GivebackRule = { mode: Mode; min_gain?: string | null; share?: string | null };
export type Basket = { id: string; name: string; drawdown?: DrawdownRule; giveback?: GivebackRule };

/** Where one ticker's level comes from, as the server resolves it. */
export type Rule = { source: "default" | "basket" | "off"; basket: string | null; threshold?: string | null; min_gain?: string | null; share?: string | null };

export type Draft = { drawdown: Mode; threshold: string; giveback: Mode; minGain: string; share: string };

/** A ratio as the percent the owner typed: "0.075" → "7,5". */
export function percentOf(ratio: string): string {
  return String(Math.round(Number(ratio) * 100 * 1e6) / 1e6).replace(".", ",");
}

/** "giỏ Ngắn hạn: 7%", "mức chung: 30%", "giỏ Dài hạn: không nhắc"; for Lãi đã trả lại "lãi từ 20%, trả lại từ 50%" or "chưa đặt". */
export function ruleLabel(rule: Rule): string {
  const head = rule.source === "default" ? "mức chung" : `giỏ ${rule.basket}`;
  if (rule.source === "off") return `${head}: không nhắc`;
  if ("threshold" in rule) return `${head}: ${percentOf(rule.threshold ?? "0")}%`;
  if (!rule.min_gain || !rule.share) return `${head}: chưa đặt`;
  return `${head}: lãi từ ${percentOf(rule.min_gain)}%, trả lại từ ${percentOf(rule.share)}%`;
}

export function draftOf(b: Basket): Draft {
  const d = b.drawdown ?? { mode: "default" }, g = b.giveback ?? { mode: "default" };
  return { drawdown: d.mode, threshold: d.mode === "custom" && d.threshold ? percentOf(d.threshold) : "",
    giveback: g.mode, minGain: g.mode === "custom" && g.min_gain ? percentOf(g.min_gain) : "", share: g.mode === "custom" && g.share ? percentOf(g.share) : "" };
}

const within = (ratio: string | null, low: number, high: number) => ratio !== null && Number(ratio) >= low && Number(ratio) <= high;

/** The fields as the basket's two rules, or what is wrong with them (the same limits as the common levels in Cài đặt). */
export function rulesFrom(d: Draft): { drawdown: DrawdownRule; giveback: GivebackRule } | string {
  let drawdown: DrawdownRule = { mode: d.drawdown };
  if (d.drawdown === "custom") {
    const t = percentInput(d.threshold);
    if (!within(t, 0.01, 0.95)) return "Sụt giảm: nhập ngưỡng riêng từ 1% đến 95%.";
    drawdown = { mode: "custom", threshold: t };
  }
  let giveback: GivebackRule = { mode: d.giveback };
  if (d.giveback === "custom") {
    const a = percentInput(d.minGain), b = percentInput(d.share);
    if (!within(a, 0.01, 10) || !within(b, 0.01, 1)) return "Lãi đã trả lại: nhập cả hai ngưỡng riêng (lãi từ 1% đến 1000%, trả lại từ 1% đến 100%).";
    giveback = { mode: "custom", min_gain: a, share: b };
  }
  return { drawdown, giveback };
}

/** Holdings whose basket does not remind: "KDH (giỏ Dài hạn)". */
export function offList(rows: { symbol: string; rule?: Rule }[]): string {
  return rows.filter((r) => r.rule?.source === "off").map((r) => `${r.symbol} (giỏ ${r.rule?.basket})`).join(", ");
}
