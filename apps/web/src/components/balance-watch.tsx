"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type DebtRow = { quarter: string; debt: string | null; cash: string | null; net_debt: string | null; net_cash: boolean | null; debt_to_equity: string | null };
type Flag = { kind: "fast_borrowing" | null; quarter: string | null; debt: string | null; debt_2y_ago: string | null; ratio: string | null };
type SectorDebt = { members: number; growth_2y: string | null; compared: number; top: string | null;
  quarters: { quarter: string; count: number; debt: string | null; net_debt: string | null; net_count: number }[] };
type CashRow = { quarter: string; advances: string | null; inventory: string | null; cfo: string | null; npat_parent: string | null };
type Signal = { kind: "handover" | "collecting" | null; quarter: string | null; advances_yoy: string | null; profit_yoy: string | null };
type LiquidityRow = { quarter: string; cash: string | null; st_investments: string | null; cash_like: string | null; st_debt: string | null;
  cover: string | null; cash_share: string | null };
export type Carry = { quarter: string | null; kind: "carry" | "no_debt" | "unusual_income" | "low_interest" | null; missing: string[]; fin_income: string | null; interest: string | null;
  net: string | null; avg_cash_like: string | null; avg_debt: string | null; yield: string | null; cost: string | null; spread: string | null };
type ArRow = { quarter: string; customers: string | null; prepay: string | null; loans: string | null; other: string | null; provision: string | null;
  total: string | null; gross?: string | null; coverage?: string | null; total_share: string | null; other_share: string | null; dso: string | null;
  prepay_days: string | null };
export type Dso = { quarter: string | null; days: string | null; year_ago: string | null; change: string | null; sector_median: string | null; sector_count: number };
export type OtherVsSector = { quarter: string | null; share: string | null; sector_median: string | null; sector_count: number; high: boolean | null };
export type RaiseEvent = { issue_date: string; quarter: string; capital_added: string; prepay_before: string | null; prepay_after: string | null;
  after_quarter: string; prepay_added: string | null; flag: boolean };
export type Provision = { quarter: string | null; amount: string | null; share: string | null; year_ago: string | null; kind: "jump" | "none" | null };
type Balance = { symbol: string; sector: string | null; debt: { rows: DebtRow[]; flag: Flag }; sector_debt: SectorDebt | null;
  property: { rows: CashRow[]; signal: Signal } | null; liquidity: LiquidityRow[]; carry: Carry;
  receivables: { rows: ArRow[]; dso: Dso; provision: Provision; prepay_days: Dso; other_vs_sector: OtherVsSector }; raise_prepay: { flag: boolean; events: RaiseEvent[] };
  revisions?: Revision[]; lending?: Lending; provision_flow?: ProvisionFlow; inventory?: Inventory;
  inventory_pace?: InventoryPace; inventory_provision_flow?: InventoryFlow; gross_loss?: GrossLoss };
export type GrossLoss = { quarter: string | null; gross_profit: string | null; coverage: string | null; coverage_prev: string | null; share: string | null;
  flag: boolean | null };
type InvFlowRow = { quarter: string; balance: string | null; change: string | null; pbt: string | null; share: string | null; kind: "release" | "charge" | null };
export type InventoryFlow = { rows: InvFlowRow[]; quarter: string | null; kind: "release" | "charge" | null };
export type InventoryPace = Dso & { inventory_growth: string | null; cogs_growth: string | null; share?: string | null; flag: boolean | null };
type InvRow = { quarter: string; gross: string | null; provision: string | null; net: string | null; coverage: string | null; share: string | null };
export type Inventory = { rows: InvRow[] };
type FlowRow = { quarter: string; balance: string | null; change: string | null; pbt: string | null; share: string | null; release: boolean };
export type ProvisionFlow = { rows: FlowRow[]; flag: boolean; quarter: string | null };
export type Lending = { quarter: string | null; share: string | null; year_ago: string | null; flag: "high" | "rising" | null };
export type Revision = { kind: "years" | "quarters"; period: string; line: string; label: string; old: string; new: string; seen_on: string };

const SHOWN = 8;  // quarters in each table
const q = (p: string) => `Q${p.slice(-1)}/${p.slice(0, 4)}`;
const ty = (v: string | null) => (v === null ? "—" : `${Math.round(Number(v) / 1e9).toLocaleString("vi-VN")} tỷ`);
const pct = (v: string) => `${Math.round(Math.abs(Number(v)) * 100).toLocaleString("vi-VN")}%`;
const move = (v: string) => `${Number(v) >= 0 ? "tăng" : "giảm"} ${pct(v)}`;

/** The warning line when borrowing at least doubled in two years; null otherwise. */
export function borrowingText(f: Flag): string | null {
  if (f.kind !== "fast_borrowing" || !f.quarter || f.debt === null) return null;
  const grew = f.ratio !== null
    ? `gấp ${Number(f.ratio).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} lần hai năm trước (${ty(f.debt_2y_ago)})`
    : "trong khi hai năm trước không vay";
  return `Nợ vay ${q(f.quarter)} là ${ty(f.debt)}, ${grew}. Vay tăng nhanh làm tăng chi phí lãi và rủi ro khi lãi suất lên: đọc thuyết minh xem vay cho dự án nào.`;
}

/** What the customer advances say about the latest quarter. */
export function advancesText(s: Signal): string {
  if (!s.quarter || s.advances_yoy === null) return "Chưa đủ số để so tiền khách trả trước với cùng kỳ năm trước.";
  if (s.kind === "handover") {
    return `${q(s.quarter)}: lợi nhuận ${s.profit_yoy !== null ? `tăng ${pct(s.profit_yoy)} so cùng kỳ` : "chuyển từ lỗ sang lãi"} trong khi tiền khách trả trước giảm ${pct(s.advances_yoy)}. `
      + "Lợi nhuận đang đến từ bàn giao những căn khách đã trả tiền trước đó, không phải từ tiền mới thu vào; xem dự án nào còn mở bán để thu tiền tiếp.";
  }
  if (s.kind === "collecting") {
    return `${q(s.quarter)}: tiền khách trả trước tăng ${pct(s.advances_yoy)} so cùng kỳ. Doanh nghiệp đã thu tiền mở bán; lợi nhuận chỉ được ghi nhận khi bàn giao, `
      + "thường sau một đến hai năm (quan sát chung của ngành, không phải dự báo cho mã này).";
  }
  return `${q(s.quarter)}: tiền khách trả trước ${move(s.advances_yoy)} so cùng kỳ: chưa rõ chiều nào. Ngưỡng của phần mềm: giảm từ 10% kèm lợi nhuận tăng từ 50% `
    + "là đang bàn giao; tăng từ 20% là đang thu tiền chờ bàn giao.";
}

const rate = (v: string) => `${(Number(v) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;

/** Chênh lệch lãi vay – lãi gửi over the last four quarters, in words. */
export function carryText(c: Carry): string {
  if (!c.quarter) return "Báo cáo đã lưu chưa có doanh thu tài chính, nên chưa tính được.";
  if (c.missing.length) return `Chưa đủ bốn quý liên tiếp đến ${q(c.quarter)} để tính: thiếu số của ${c.missing.map(q).join(", ")}.`;
  const earned = `doanh thu tài chính ${ty(c.fin_income)} trên tiền và đầu tư ngắn hạn bình quân ${ty(c.avg_cash_like)}`
    + (c.yield !== null ? ` (khoảng ${rate(c.yield)}/năm)` : "");
  if (c.kind === "no_debt") return `Bốn quý đến ${q(c.quarter)}: không vay; ${earned}.`;
  const paid = `lãi vay ${ty(c.interest)} trên nợ vay bình quân ${ty(c.avg_debt)}${c.cost !== null ? ` (khoảng ${rate(c.cost)}/năm)` : ""}`;
  const gap = c.spread === null ? "" : ` Chênh lệch ${Number(c.spread) >= 0 ? "+" : "−"}${rate(String(Math.abs(Number(c.spread)))).replace("%", "")} điểm %.`;
  const verdict = c.kind === "carry"
    ? " Doanh nghiệp vừa vay vừa giữ nhiều tiền và thu từ tiền nhiều hơn trả lãi vay: kiểu \"vay rẻ, gửi đắt\"."
    : c.kind === "unusual_income"
      ? " Mức trên 10%/năm cao hơn mọi lãi tiền gửi: doanh thu tài chính còn gồm lãi tỷ giá, lãi bán hoặc lãi từ khoản đầu tư, cho vay; đọc thuyết minh, không coi là lãi gửi."
      : c.kind === "low_interest"
        ? " Chi phí vay dưới 2%/năm thấp hơn mọi lãi vay ngân hàng: lãi vay có thể đã được vốn hóa vào dự án hoặc tài sản dở dang (thường gặp ở bất động sản); đọc thuyết minh."
        : c.spread !== null && Number(c.spread) < 0 ? " Thu từ tiền thấp hơn chi phí vay." : "";
  return `Bốn quý đến ${q(c.quarter)}: ${earned}; ${paid}.${gap}${verdict}`;
}

/** Số ngày thu tiền of the latest quarter, against a year before and the sector. */
export function dsoText(d: Dso): string {
  if (!d.quarter || d.days === null) return "Chưa đủ phải thu khách hàng và doanh thu bốn quý để tính số ngày thu tiền.";
  const ago = d.change !== null
    ? Number(d.change) === 0 ? ", bằng cùng kỳ năm trước" : `, ${Number(d.change) > 0 ? "chậm hơn" : "nhanh hơn"} ${Math.abs(Number(d.change))} ngày so với cùng kỳ năm trước (${d.year_ago} ngày)`
    : "";
  const peers = d.sector_median !== null ? `; trung vị ngành ${d.sector_median} ngày (${d.sector_count} mã theo dõi khác)` : "";
  return `Số ngày thu tiền ${q(d.quarter)}: ${d.days} ngày${ago}${peers}.`;
}

/** Số ngày ứng trước nhà cung cấp of the latest quarter, against a year before and the sector. */
export function prepayDaysText(d: Dso): string {
  if (!d.quarter || d.days === null) return "Chưa đủ trả trước người bán và giá vốn bốn quý để tính số ngày ứng trước.";
  const ago = d.change !== null
    ? Number(d.change) === 0 ? ", bằng cùng kỳ năm trước" : `, ${Number(d.change) > 0 ? "dài hơn" : "ngắn hơn"} ${Math.abs(Number(d.change))} ngày so với cùng kỳ năm trước (${d.year_ago} ngày)`
    : "";
  const peers = d.sector_median !== null ? `; trung vị ngành ${d.sector_median} ngày (${d.sector_count} mã theo dõi khác)` : "";
  return `Số ngày ứng trước nhà cung cấp ${q(d.quarter)}: ${d.days} ngày${ago}${peers}.`;
}

/** Other receivables and loans against total assets, set against the sector's median. */
export function otherSectorText(o: OtherVsSector): string {
  if (!o.quarter || o.share === null) return "Chưa đủ phải thu khác và tổng tài sản để so với ngành.";
  const own = `Phải thu khác và cho vay ${q(o.quarter)} bằng ${rate(o.share)} tổng tài sản`;
  if (o.sector_median === null) return `${own}; chưa có mã cùng ngành nào trong danh sách theo dõi để so.`;
  const verdict = o.high ? " Cao hơn hẳn các mã cùng ngành: không phải đặc thù ngành, nên đọc thuyết minh xem phải thu của ai." : "";
  return `${own}; trung vị ngành ${rate(o.sector_median)} (${o.sector_count} mã theo dõi khác).${verdict}`;
}

/** One money-raising issue and what prepayments to suppliers did around it. */
export function raiseText(e: RaiseEvent): string {
  const day = e.issue_date.split("-").reverse().join("/");
  if (e.prepay_added === null) return `Đợt huy động vốn ngày ${day} (vốn điều lệ thêm ${ty(e.capital_added)}, ${q(e.quarter)}): thiếu số trả trước người bán để so.`;
  const moved = `trả trước người bán từ ${ty(e.prepay_before)} (trước đợt) lên ${ty(e.prepay_after)} (${q(e.after_quarter)})`;
  return e.flag
    ? `Đợt huy động vốn ngày ${day} thêm ${ty(e.capital_added)} vốn điều lệ (${q(e.quarter)}); ngay sau đó ${moved}, tăng ${ty(e.prepay_added)}, từ một nửa số vốn vừa góp. `
      + "Tiền vừa huy động có thể đã chuyển ra ngoài dưới danh nghĩa ứng trước: đọc thuyết minh xem trả trước cho ai, có phải bên liên quan không, và đã nhận hàng chưa."
    : `Đợt huy động vốn ngày ${day} thêm ${ty(e.capital_added)} vốn điều lệ (${q(e.quarter)}); ${moved}, thấp hơn một nửa số vốn vừa góp.`;
}

/** The bad-debt provision of the latest quarter, in words. */
/** Cho vay và phải thu khác so với vốn chủ (22/11/2026): the latest quarter against a year before, and why it is flagged. */
export function lendingText(l: Lending): string {
  if (!l.quarter || l.share === null) return "Chưa tính được cho vay và phải thu khác so với vốn chủ (thiếu dòng phải thu hoặc vốn chủ không dương).";
  const ago = l.year_ago !== null ? `; cùng kỳ năm trước ${rate(l.year_ago)}` : "";
  const why = l.flag === "high" ? " Từ 30% vốn chủ: xem ai đang vay, có phải bên liên quan không (Sổ phải thu bên liên quan)."
    : l.flag === "rising" ? " Tăng từ 10 điểm trong một năm: xem khoản cho vay mới là của ai." : "";
  return `${q(l.quarter)}: cho vay và phải thu khác bằng ${rate(l.share)} vốn chủ${ago}.${why}`;
}

/** Dự phòng đi vào lợi nhuận (22/11/2026): the latest quarter's change of the provision balance against its profit before tax. */
export function provisionFlowText(f: ProvisionFlow): string {
  const r = f.rows[f.rows.length - 1];
  if (!r || r.change === null) return "Chưa tính được thay đổi dự phòng phải thu trong quý (thiếu số dư dự phòng của quý này hoặc quý trước).";
  const up = Number(r.change) >= 0;
  const share = r.share !== null ? `, bằng ${rate(r.share)} LNTT của quý` : r.pbt !== null ? " (LNTT của quý không dương: không tính tỷ lệ)" : "";
  const main = `${q(r.quarter)}: dự phòng phải thu ${up ? "tăng" : "giảm"} ${ty(String(Math.abs(Number(r.change))))}${share}.`;
  return up ? main : `${main} Số dư giảm có thể do hoàn nhập (làm tăng lợi nhuận) hoặc do xóa nợ (không ảnh hưởng lợi nhuận); nguồn công khai không tách được, cần xem thuyết minh.`;
}

/** Mức bao phủ dự phòng over the 12 quarters (22/11/2026): the latest against a year before and the first of the 12. */
export function coverageText(rows: ArRow[]): string {
  const known = rows.filter((r) => r.coverage != null);
  const last = known[known.length - 1];
  if (!last) return "Chưa tính được mức bao phủ dự phòng (thiếu dòng dự phòng hoặc phải thu).";
  const back = (n: number) => { const [y, k] = last.quarter.split("-Q").map(Number); const i = y * 4 + k - 1 - n; return `${Math.floor(i / 4)}-Q${(i % 4) + 1}`; };
  const ago = known.find((r) => r.quarter === back(4));
  const first = known[0] !== last ? known[0] : undefined;
  const parts = [ago ? `cùng kỳ năm trước ${rate(ago.coverage!)}` : null, first && first !== ago ? `${q(first.quarter)} ${rate(first.coverage!)}` : null].filter(Boolean);
  return `${q(last.quarter)}: dự phòng bằng ${rate(last.coverage!)} phải thu trước dự phòng (${ty(last.gross ?? null)}), giá trị thuần ${ty(last.total)}`
    + (parts.length ? `; ${parts.join("; ")}.` : ".");
}

/** Dự phòng giảm giá tồn kho đi vào lợi nhuận (22/11/2026): the latest quarter's change against its profit before tax. */
export function inventoryFlowText(f: InventoryFlow): string {
  const r = f.rows[f.rows.length - 1];
  if (!r || r.change === null) return "Chưa tính được thay đổi dự phòng giảm giá tồn kho trong quý (thiếu số dư của quý này hoặc quý trước).";
  const up = Number(r.change) >= 0;
  const share = r.share !== null ? `, bằng ${rate(r.share)} LNTT của quý` : r.pbt !== null ? " (LNTT của quý không dương: không tính tỷ lệ)" : "";
  const main = `${q(r.quarter)}: dự phòng giảm giá tồn kho ${up ? "tăng" : "giảm"} ${ty(String(Math.abs(Number(r.change))))}${share}.`;
  if (up) return r.kind === "charge" ? `${main} Trích thêm lớn: hàng đang mất giá, xem thuyết minh loại hàng nào.` : main;
  return `${main} Số dư giảm có thể do hoàn nhập (làm tăng lợi nhuận) hoặc do hàng đã bán, đã hủy; nguồn công khai không tách được, cần xem thuyết minh.`;
}

/** Tồn kho tăng nhanh hơn sức bán (22/11/2026): the days inventory lasts, against a year before and the sector, and the growth of
 * inventory against four quarters' cost of sales. */
export function inventoryPaceText(p: InventoryPace): string {
  if (!p.quarter || p.days === null) return "Chưa tính được số ngày tồn kho (thiếu tồn kho hoặc giá vốn bốn quý).";
  const ago = p.year_ago !== null ? `; cùng kỳ năm trước ${p.year_ago} ngày` : "";
  const sector = p.sector_median !== null ? `; trung vị ngành ${p.sector_median} ngày (${p.sector_count} mã)` : "";
  const growth = p.inventory_growth !== null && p.cogs_growth !== null
    ? ` Tồn kho tăng ${rate(p.inventory_growth)} so cùng kỳ, giá vốn bốn quý tăng ${rate(p.cogs_growth)}.` : "";
  const small = !p.flag && p.share != null && Number(p.share) < 0.1 ? ` Tồn kho chỉ ${rate(p.share)} tổng tài sản: không ghi cờ.` : "";
  const why = p.flag ? " Hàng nhập về nhanh hơn hàng bán ra: xem thuyết minh tồn kho (loại hàng nào tăng) và dự phòng giảm giá." : small;
  return `${q(p.quarter)}: tồn kho đủ ${p.days} ngày giá vốn${ago}${sector}.${growth}${why}`;
}

/** Bán dưới giá vốn nhưng dự phòng không tăng (23/11/2026): only a quarter with a gross loss says anything. */
export function grossLossText(g: GrossLoss): string | null {
  if (!g.quarter || g.gross_profit === null || Number(g.gross_profit) >= 0) return null;
  const cover = g.coverage !== null && g.coverage_prev !== null
    ? `, tỷ lệ trích lập dự phòng tồn kho ${rate(g.coverage)} (quý trước ${rate(g.coverage_prev)})` : "";
  const main = `${q(g.quarter)}: lỗ gộp ${ty(String(-Number(g.gross_profit)))} (bán dưới giá vốn)${cover}.`;
  if (g.flag) return `${main} Giá trị thuần có thể thu hồi đã thấp hơn giá ghi sổ mà dự phòng chưa tăng: xem thuyết minh hàng tồn kho.`;
  if (g.coverage !== null && g.coverage_prev !== null && Number(g.coverage) > Number(g.coverage_prev)) return `${main} Tỷ lệ trích lập dự phòng đã tăng theo.`;
  return main;
}

/** Khối Tồn kho (22/11/2026): the latest quarter net, its share of total assets and the share provided for, against a year before. */
export function inventoryText(inv: Inventory): string {
  const last = inv.rows[inv.rows.length - 1];
  if (!last || last.net === null) return "Báo cáo đã lưu chưa có dòng hàng tồn kho.";
  const [y, k] = last.quarter.split("-Q").map(Number);
  const ago = inv.rows.find((r) => r.quarter === `${y - 1}-Q${k}`);
  const share = last.share !== null ? `, bằng ${rate(last.share)} tổng tài sản` : "";
  const cover = last.coverage !== null ? `; dự phòng giảm giá ${ty(last.provision)}, bằng ${rate(last.coverage)} giá gốc ${ty(last.gross)}` : "; chưa có giá gốc và dự phòng của quý này";
  const before = ago && ago.net !== null ? ` Cùng kỳ năm trước: ${ty(ago.net)}${ago.share !== null ? ` (${rate(ago.share)} tổng tài sản)` : ""}.` : "";
  return `${q(last.quarter)}: tồn kho thuần ${ty(last.net)}${share}${cover}.${before}`;
}

/** One figure the source changed for a closed period (Số đã công bố bị sửa, 22/11/2026): old → new and the day seen; no cause inferred. */
export function revisionText(r: Revision): string {
  const when = r.kind === "years" ? `Năm ${r.period}` : `Quý ${r.period.slice(-1)}/${r.period.slice(0, 4)}`;
  const seen = `${r.seen_on.slice(8, 10)}/${r.seen_on.slice(5, 7)}/${r.seen_on.slice(0, 4)}`;
  return `${when}, ${r.label}: ${ty(r.old)} → ${ty(r.new)} (thấy ${seen})`;
}

export function provisionText(p: Provision): string {
  if (!p.quarter || p.amount === null) return "Báo cáo đã lưu chưa có dòng dự phòng phải thu khó đòi.";
  if (p.kind === "none") return `${q(p.quarter)}: không trích dự phòng phải thu ngắn hạn khó đòi.`;
  const share = p.share !== null ? `, bằng ${rate(p.share)} phải thu ngắn hạn trước dự phòng` : "";
  const jump = p.kind === "jump" ? ` Tăng mạnh so với cùng kỳ năm trước (${ty(p.year_ago)}): doanh nghiệp vừa thừa nhận thêm khoản khó thu; đọc thuyết minh xem của khách hàng nào.` : "";
  return `${q(p.quarter)}: dự phòng phải thu ngắn hạn khó đòi ${ty(p.amount)}${share}.${jump}`;
}

/** One line on the sector's borrowing. */
export function sectorText(sector: string, s: SectorDebt): string | null {
  const last = s.quarters.at(-1);
  if (!last || last.debt === null) return null;
  const net = last.net_debt !== null ? `, nợ vay ròng ${ty(last.net_debt)}${last.net_count < last.count ? ` (${last.net_count} mã)` : ""}` : "";
  const two = s.growth_2y !== null
    ? ` So với hai năm trước: ${move(s.growth_2y)} trên ${s.compared} mã có đủ số${s.top ? `, tăng nhiều nhất là ${s.top}` : ""}.`
    : " Chưa đủ số để so với hai năm trước.";
  return `Ngành ${sector} (${s.members} mã theo dõi, ${last.count} mã có số ${q(last.quarter)}): tổng nợ vay ${ty(last.debt)}${net}.${two}`;
}

export function BalanceWatch({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Balance | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<Balance>(`stock/${encodeURIComponent(symbol)}/balance`).then(setData, (e) => {
      if (e instanceof ApiError && ["not_applicable", "symbol_not_watched"].includes(e.failure.code)) return;  // banks and insurers read their own figures
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
    });
  }, [symbol]);
  if (message) return <section className="surface" aria-label="Nợ vay ròng"><h2>Nợ vay ròng</h2><p className="muted">{message}</p></section>;
  if (!data) return null;
  const rows = data.debt.rows.slice(-SHOWN).reverse();
  const latest = data.debt.rows.at(-1);
  const warn = borrowingText(data.debt.flag);
  const sector = data.sector && data.sector_debt ? sectorText(data.sector, data.sector_debt) : null;
  return (
    <>
      <section className="surface" aria-label="Nợ vay ròng">
        <h2>Nợ vay ròng</h2>
        {warn && <p className="notice" data-testid="borrowing-flag">{warn}</p>}
        {latest?.net_cash && <p><span className="pill good">Tiền ròng</span> {q(latest.quarter)}: tiền và đầu tư ngắn hạn nhiều hơn nợ vay {ty(String(-Number(latest.net_debt)))}.</p>}
        <table className="fv-table" aria-label={`Nợ vay ròng ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Nợ vay</th><th className="num">Tiền và đầu tư ngắn hạn</th><th className="num">Nợ vay ròng</th><th className="num">Nợ vay / vốn chủ</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Nợ vay">{ty(r.debt)}</td>
              <td className="num" data-label="Tiền và đầu tư ngắn hạn">{ty(r.cash)}</td>
              <td className={`num${r.net_cash ? " positive" : ""}`} data-label="Nợ vay ròng">{ty(r.net_debt)}</td>
              <td className="num" data-label="Nợ vay / vốn chủ">{r.debt_to_equity === null ? "—" : `${Number(r.debt_to_equity).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} lần`}</td>
            </tr>))}
          </tbody>
        </table>
        {sector && <p data-testid="sector-debt">{sector}</p>}
        <p className="caption">Nợ vay = vay ngắn hạn + vay dài hạn; nợ vay ròng = nợ vay − tiền − đầu tư ngắn hạn, âm là tiền ròng. Cảnh báo khi nợ vay gấp từ 2 lần
          tám quý trước và bằng từ 5% tổng tài sản. Báo cáo công khai (VNDirect); ô thiếu số để trống. Không phải khuyến nghị.</p>
      </section>
      <section className="surface" aria-label="Tiền và chênh lệch lãi suất">
        <h2>Tiền và chênh lệch lãi suất</h2>
        <p data-testid="carry">{data.carry.kind === "carry" && <><span className="pill good">Vay rẻ, gửi đắt</span> </>}{carryText(data.carry)}</p>
        <table className="fv-table" aria-label={`Thang thanh khoản ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Tiền và tương đương tiền</th><th className="num">Đầu tư tài chính ngắn hạn</th>
            <th className="num">Vay ngắn hạn</th><th className="num">Tiền + đầu tư NH / vay NH</th><th className="num">Trên tổng tài sản</th></tr></thead>
          <tbody>{data.liquidity.slice(-SHOWN).reverse().map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Tiền và tương đương tiền">{ty(r.cash)}</td>
              <td className="num" data-label="Đầu tư tài chính ngắn hạn">{ty(r.st_investments)}</td>
              <td className="num" data-label="Vay ngắn hạn">{ty(r.st_debt)}</td>
              <td className={`num${r.cover !== null && Number(r.cover) < 1 ? " negative" : ""}`} data-label="Tiền + đầu tư NH / vay NH">
                {r.cover === null ? "—" : `${Number(r.cover).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} lần`}</td>
              <td className="num" data-label="Trên tổng tài sản">{r.cash_share === null ? "—" : rate(r.cash_share)}</td>
            </tr>))}
          </tbody>
        </table>
        <p className="caption">Tiền và tương đương tiền gồm cả tiền gửi kỳ hạn đến 3 tháng; đầu tư tài chính ngắn hạn chủ yếu là tiền gửi 3–12 tháng (có thể có cả
          chứng khoán kinh doanh). Dưới 1 lần: tiền và đầu tư ngắn hạn chưa đủ trả vay ngắn hạn. Lợi suất trên tiền là ước tính thô: doanh thu tài chính còn gồm lãi
          tỷ giá, cổ tức và lãi bán khoản đầu tư; bình quân trên năm thời điểm cuối quý. “Vay rẻ, gửi đắt” khi nợ vay và tiền đều từ 5% tổng tài sản và chênh lệch
          dương, lợi suất trên tiền không quá 10%/năm và chi phí vay từ 2%/năm. Báo cáo công khai (VNDirect). Không phải khuyến nghị.</p>
      </section>
      <section className="surface" aria-label="Phải thu">
        <h2>Phải thu</h2>
        <p data-testid="dso">{dsoText(data.receivables.dso)}</p>
        <p data-testid="other-sector">{data.receivables.other_vs_sector.high && <><span className="pill warn">Cao hơn hẳn ngành</span> </>}
          {otherSectorText(data.receivables.other_vs_sector)}</p>
        <p data-testid="prepay-days">{prepayDaysText(data.receivables.prepay_days)}</p>
        {data.raise_prepay.events.map((e) => <p key={e.issue_date} data-testid="raise-prepay" className={e.flag ? "notice" : undefined}>
          {e.flag && <><span className="pill warn">Trả trước tăng sau huy động vốn</span> </>}{raiseText(e)}</p>)}
        {data.lending && <p data-testid="lending">{data.lending.flag && <><span className="pill warn">Cho vay lớn so với vốn chủ</span> </>}{lendingText(data.lending)}</p>}
        {data.provision_flow && <p data-testid="provision-flow">{data.provision_flow.flag && <><span className="pill warn">Giảm dự phòng lớn so với lợi nhuận</span> </>}{provisionFlowText(data.provision_flow)}</p>}
        <p data-testid="provision">{data.receivables.provision.kind === "jump" && <><span className="pill warn">Dự phòng tăng mạnh</span> </>}
          {provisionText(data.receivables.provision)}</p>
        <p data-testid="coverage">{coverageText(data.receivables.rows)}</p>
        <div className="tablewrap"><table className="fv-table" aria-label={`Phải thu ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Khách hàng</th><th className="num">Trả trước người bán</th><th className="num">Cho vay</th>
            <th className="num">Phải thu khác</th><th className="num">Dự phòng</th><th className="num">Trước dự phòng</th><th className="num">Bao phủ</th><th className="num">Giá trị thuần</th><th className="num">Trên tổng tài sản</th>
            <th className="num">Số ngày thu tiền</th><th className="num">Số ngày ứng trước</th></tr></thead>
          <tbody>{data.receivables.rows.slice(-SHOWN).reverse().map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Khách hàng">{ty(r.customers)}</td>
              <td className="num" data-label="Trả trước người bán">{ty(r.prepay)}</td>
              <td className="num" data-label="Cho vay">{ty(r.loans)}</td>
              <td className="num" data-label="Phải thu khác">{ty(r.other)}{r.other_share !== null && <span className="caption"> ({rate(r.other_share)} TS)</span>}</td>
              <td className="num" data-label="Dự phòng">{ty(r.provision)}</td>
              <td className="num" data-label="Trước dự phòng">{ty(r.gross ?? null)}</td>
              <td className="num" data-label="Bao phủ">{r.coverage == null ? "—" : rate(r.coverage)}</td>
              <td className="num" data-label="Giá trị thuần">{ty(r.total)}</td>
              <td className="num" data-label="Trên tổng tài sản">{r.total_share === null ? "—" : rate(r.total_share)}</td>
              <td className="num" data-label="Số ngày thu tiền">{r.dso === null ? "—" : `${r.dso} ngày`}</td>
              <td className="num" data-label="Số ngày ứng trước">{r.prepay_days === null ? "—" : `${r.prepay_days} ngày`}</td>
            </tr>))}
          </tbody>
        </table></div>
        <p className="caption">Mỗi cột cộng phần ngắn hạn và dài hạn (trả trước người bán: ngắn hạn); dự phòng mang dấu âm, đã trừ trong tổng. Số ngày thu tiền = phải
          thu khách hàng ngắn hạn cuối quý ÷ doanh thu bốn quý gần nhất × 365; trung vị ngành trên các mã theo dõi cùng ngành. Dự phòng được ghi là tăng mạnh khi
          tăng từ 50% so với cùng kỳ và bằng từ 1% phải thu ngắn hạn. Số ngày ứng trước = trả trước người bán cuối quý ÷ giá vốn bốn quý × 365: khoản này
          được thu hồi bằng hàng hóa, dịch vụ chứ không bằng tiền. Đợt huy động vốn (không tính cổ phiếu thưởng) được ghi nhận khi trả trước tăng từ một
          nửa số vốn điều lệ vừa thêm, trong quý ghi nhận vốn và quý kế tiếp. Phải thu từ bên liên quan và tên từng khách hàng chỉ có trong thuyết minh, không có ở đây.
          Từ năm 2026, Thông tư 99 bỏ chỉ tiêu phải thu về cho vay và gộp khoản cho vay vào phải thu khác: cột Cho vay về 0, cột Phải thu khác tăng
          tương ứng; khi so qua năm hãy cộng hai cột. Báo cáo công khai (VNDirect); ô thiếu số để trống. Không phải khuyến nghị.</p>
      </section>
      <section className="surface" aria-label="Số đã công bố bị sửa">
        <h2>Số đã công bố bị sửa</h2>
        {data.revisions && data.revisions.length > 0
          ? <ul className="ye-list">{data.revisions.map((r) => <li key={`${r.kind}${r.period}${r.line}${r.new}`}>{revisionText(r)}</li>)}</ul>
          : <p className="muted">Chưa thấy lần sửa nào.</p>}
        <p className="caption">Từ 22/11/2026, mỗi lần đồng bộ hằng tuần đọc lại hai năm báo cáo gần nhất; số của một kỳ đã đóng (LNST công ty mẹ, LNTT, vốn chủ,
          dự phòng phải thu) đổi quá cả 1% và 1 tỷ thì được ghi lại. Có thể do điều chỉnh hồi tố hoặc nguồn sửa lỗi nhập; xem thuyết minh và báo cáo kiểm
          toán. Lần sửa trước ngày đó hoặc cũ hơn hai năm không dựng lại được.</p>
      </section>
      {data.inventory && <section className="surface" aria-label="Tồn kho">
        <h2>Tồn kho</h2>
        <p data-testid="inventory">{inventoryText(data.inventory)}</p>
        {data.inventory_provision_flow && <p data-testid="inventory-flow">{data.inventory_provision_flow.kind && <><span className="pill warn">
          {data.inventory_provision_flow.kind === "release" ? "Hoàn nhập dự phòng tồn kho lớn" : "Trích thêm dự phòng tồn kho lớn"}</span> </>}
          {inventoryFlowText(data.inventory_provision_flow)}</p>}
        {data.inventory_pace && <p data-testid="inventory-pace">{data.inventory_pace.flag && <><span className="pill warn">Tồn kho tăng nhanh hơn giá vốn</span> </>}
          {inventoryPaceText(data.inventory_pace)}</p>}
        {data.gross_loss && grossLossText(data.gross_loss) && <p data-testid="gross-loss">{data.gross_loss.flag && <><span className="pill warn">
          Bán dưới giá vốn, dự phòng không tăng</span> </>}{grossLossText(data.gross_loss)}</p>}
        <div className="tablewrap"><table className="fv-table" aria-label={`Tồn kho ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Giá gốc</th><th className="num">Dự phòng giảm giá</th><th className="num">Bao phủ</th>
            <th className="num">Giá trị thuần</th><th className="num">Trên tổng tài sản</th></tr></thead>
          <tbody>{data.inventory.rows.slice(-SHOWN).reverse().map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Giá gốc">{ty(r.gross)}</td>
              <td className="num" data-label="Dự phòng giảm giá">{ty(r.provision)}</td>
              <td className="num" data-label="Bao phủ">{r.coverage === null ? "—" : rate(r.coverage)}</td>
              <td className="num" data-label="Giá trị thuần">{ty(r.net)}</td>
              <td className="num" data-label="Trên tổng tài sản">{r.share === null ? "—" : rate(r.share)}</td>
            </tr>))}</tbody>
        </table></div>
        <p className="caption">Giá gốc và dự phòng giảm giá hàng tồn kho theo bảng cân đối (VNDirect); giá trị thuần = giá gốc − dự phòng. Bao phủ = dự phòng ÷
          giá gốc. Số ngày tồn kho = tồn kho thuần cuối quý ÷ giá vốn bốn quý × 365; được ghi là tăng nhanh hơn giá vốn khi tồn kho tăng so cùng kỳ
          nhanh hơn giá vốn bốn quý từ 20 điểm %, số ngày tăng và tồn kho từ 10% tổng tài sản (không ghi với Bất động sản, nơi tồn kho là dự án). Cơ cấu (nguyên vật liệu, dở dang, thành phẩm, hàng hóa) chỉ có trong thuyết minh, không có ở đây. Ô thiếu số để trống. Không phải khuyến nghị.</p>
      </section>}
      {data.property && <section className="surface" aria-label="Tiền khách trả trước">
        <h2>Tiền khách trả trước</h2>
        <p data-testid="advances-signal">{advancesText(data.property.signal)}</p>
        <table className="fv-table" aria-label={`Tiền khách trả trước ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Khách trả trước</th><th className="num">Hàng tồn kho</th><th className="num">Dòng tiền kinh doanh</th><th className="num">LNST công ty mẹ</th></tr></thead>
          <tbody>{data.property.rows.slice(-SHOWN).reverse().map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Khách trả trước">{ty(r.advances)}</td>
              <td className="num" data-label="Hàng tồn kho">{ty(r.inventory)}</td>
              <td className={`num${r.cfo !== null && Number(r.cfo) < 0 ? " negative" : ""}`} data-label="Dòng tiền kinh doanh">{ty(r.cfo)}</td>
              <td className={`num${r.npat_parent !== null && Number(r.npat_parent) < 0 ? " negative" : ""}`} data-label="LNST công ty mẹ">{ty(r.npat_parent)}</td>
            </tr>))}
          </tbody>
        </table>
        <p className="caption">Khách trả trước = người mua trả tiền trước ngắn hạn + dài hạn: tiền khách đã đóng cho căn chưa bàn giao. Khi bàn giao, khoản này giảm
          và chuyển thành doanh thu, lợi nhuận; vì vậy dòng tiền thường đi trước lợi nhuận. So với cùng quý năm trước. Không phải khuyến nghị.</p>
      </section>}
    </>
  );
}
