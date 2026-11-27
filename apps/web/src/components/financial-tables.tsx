"use client";
import { useEffect, useState } from "react";
import { ChartColumn } from "lucide-react";
import { ApiError, api } from "../lib/api";
import { type Forecast, ForecastForm } from "./quarter-forecast";
import { Spark, StatementChart, seriesName, toggleRow } from "./statement-chart";

type Row = { key: string | null; label: string; kind: "group" | "money" | "pct" | "x" | "vnd" | "days"; indent: number; values: (string | null)[] };
type Part = { periods: string[]; rows: Row[] };
type Check = { period: string; check: string; label: string; a: string | null; b: string | null };
type Conflict = { period: string; line: string; values: string[] };
type Summary = { period: string; close_date: string | null; market_cap: string | null; npat_ttm: string | null; ebitda_ttm: string | null;
  ev: string | null; pe: string | null; pb: string | null; ev_ebitda: string | null; roe: string | null; roic?: string | null; quarters: string[] };
type Tables = { symbol: string; kind?: "bank" | "securities" | "insurance" | null; reason: string | null; source?: string; fetched_at?: string; quarters: Part; years: Part; summary: Summary | null;
  checks: Check[]; conflicts: Conflict[]; fixed_assets_pending?: boolean; finance_lease?: string[];
  valuation_check?: { shares_from_vndirect?: boolean; date: string | null; ours_date: string | null; flagged: number; rows: { key: string; label: string; note?: string | null; ours: string | null; theirs: string | null; diff: string | null; off: boolean }[] } | null };

type Kind = "bank" | "securities" | "insurance";
// "general": VNDirect's ratios of a company outside banks, securities and insurance (Chỉ số tài chính (VNDirect), 26/11/2026)
type Ratios = { kind: Kind | "general"; quarters: { date: string; label: string }[];
  metrics: { code: string; label: string; format: "pct0" | "pct1" | "pct2" | "times" | "days"; values: (string | null)[] }[];
  fetched_at?: string | null; notes?: string[]; notes_fetched_at?: string | null; sector?: Sector | null };
// Trung vị ngành (26/11/2026): peers of the same ICB level-2 sector on HOSE with figures for the ticker's own latest quarter
export type Sector = { name: string; quarter: string; peers: number; medians: Record<string, string | null>; counts: Record<string, number> };  // a bank's group-2 share and CASA: quarters left blank or entered differently

const SIGNED = new Set(["revenue_yoy", "gross_profit_yoy", "npat_parent_yoy", "ebitda_yoy", "fcff_yield"]);
// VNDirect's ratios read to two places (NPL 1,66%, not 1,7%), as their own table showed them.
const TWO = new Set(["BAD_LOANS_RATIO_AQ", "GROUP2_RATIO", "CAR", "OVERDUE_LOANS_RATIO_AQ", "NET_INTEREST_MARGIN_TR_AVG5Q", "ROAA_TR_AVG4Q", "LOANS_TO_EQUITY_AQ"]);
const TITLE: Record<Kind, string> = { bank: "ngân hàng", securities: "công ty chứng khoán", insurance: "bảo hiểm" };
const COUNTS = [8, 12, 20, 0] as const;

// Cảnh báo báo cáo (26/11/2026, docs/superpowers/specs/2026-11-26-canh-bao-bang-so-tai-chinh-design.md), worked out as the MCP tools do
type Share = { ky: string | string[]; ty_le: string | null; vuot_nguong: boolean | null };
export type OutsideSales = { nguong: string; quy_gan_nhat: Share; bon_quy: Share } | null;
const pct1 = (v: string) => `${(Number(v) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;
const qText = (k: string) => `Q${k.slice(-1)}/${k.slice(0, 4)}`;

export function outsideSalesNote(f: OutsideSales): string | null {
  if (!f) return null;
  const parts: string[] = [];
  const q = f.quy_gan_nhat, y = f.bon_quy;
  if (q.vuot_nguong && q.ty_le) parts.push(`${pct1(q.ty_le)} LNTT ${qText(String(q.ky))}`);
  if (y.vuot_nguong && y.ty_le && Array.isArray(y.ky)) parts.push(`${pct1(y.ty_le)} LNTT 4 quý đến ${qText(y.ky[y.ky.length - 1])}`);
  if (!parts.length) return null;
  return `Lợi nhuận ngoài bán hàng: doanh thu tài chính và lợi nhuận khác bằng ${parts.join(", ")} (ngưỡng ${pct1(f.nguong)}). `
    + "Lãi tiền gửi đều đặn cũng nằm trong doanh thu tài chính, nên đây không hẳn là khoản một lần.";
}

export function epsNote(years: { nam: string }[] | null | undefined): string | null {
  if (!years || !years.length) return null;
  return `EPS lệch hẳn LNST công ty mẹ năm ${years.map((y) => y.nam).join(", ")} (hơn 3 lần so năm trước): `
    + "có thể là lỗi nguồn hoặc phát hành nhiều cổ phiếu; số giữ nguyên như VNDirect.";
}

// P/E, P/B so với lịch sử (26/11/2026): the ticker's own month-end P/E and P/B, worked out as dinh_gia_lich_su does
type OwnOne = { now: string | null; median_3y: string | null; median_5y: string | null; lower_3y: string | null } | null;
export type OwnHistory = { date: string; pe: OwnOne; pb: OwnOne } | null;

export function historyCards(h: OwnHistory | undefined): { title: string; value: string; sub: string | null }[] {
  if (!h) return [];
  const day = h.date.split("-").reverse().join("/");
  const fmt = (v: string | null, places: number) => (v === null ? "—" : `${Number(v).toLocaleString("vi-VN", { minimumFractionDigits: places, maximumFractionDigits: places })}x`);
  return ([["P/E", h.pe, 1], ["P/B", h.pb, 2]] as const).flatMap(([name, o, places]) => !o || (o.median_3y === null && o.median_5y === null) ? [] : [{
    title: `${name} so với lịch sử (${day})`,
    value: `${fmt(o.now, places)} · 3 năm ${fmt(o.median_3y, places)} · 5 năm ${fmt(o.median_5y, places)}`,
    sub: o.lower_3y ? `${o.lower_3y} tháng trong 3 năm thấp hơn` : null }]);
}

export type PeContext = { quarter: string; year_ago: string; ttm: string; ttm_year_ago: string; change: string | null; kind: "earnings_drop" | "earnings_spike" | "loss" | null };
const quarterText = (p: string) => `Q${p.slice(-1)}/${p.slice(0, 4)}`;
const share = (v: string) => `${(Math.abs(Number(v)) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 0 })}%`;

/** Bẫy P/E: why the P/E reads as it does when profit has moved a lot against a year before. Null when nothing needs saying. */
export function peNote(c: PeContext | null): string | null {
  if (!c || !c.kind) return null;
  if (c.kind === "loss") return `Lợi nhuận 4 quý đến ${quarterText(c.quarter)} âm nên P/E không có ý nghĩa; xem P/B hoặc chờ lợi nhuận dương trở lại.`;
  if (c.kind === "earnings_drop") return `P/E đang cao vì lợi nhuận 4 quý đến ${quarterText(c.quarter)} giảm ${share(c.change!)} so với cùng kỳ, không phải vì giá đắt. Xem lợi nhuận có hồi phục không trước khi so P/E.`;
  return `P/E đang thấp vì lợi nhuận 4 quý đến ${quarterText(c.quarter)} tăng ${share(c.change!)} so với cùng kỳ. Nếu phần tăng đến từ khoản một lần hay đỉnh chu kỳ, P/E thấp có thể không bền.`;
}

/** The quiet line for an ordinary year: how profit moved, inside the thresholds, so the P/E is not distorted. Null otherwise. */
export function peCalm(c: PeContext | null): string | null {
  if (!c || c.kind || c.change === null) return null;
  const n = Number(c.change);
  const move = n > 0 ? `tăng ${share(c.change)}` : n < 0 ? `giảm ${share(c.change)}` : "không đổi";
  return `Lợi nhuận 4 quý đến ${quarterText(c.quarter)} ${move} so với cùng kỳ, trong ngưỡng giảm 40% đến tăng 60%: P/E không bị méo vì lợi nhuận biến động mạnh.`;
}

export function cell(v: string | null, kind: Row["kind"], key: string | null): string {
  if (v === null) return "—";
  const n = Number(v);
  if (kind === "money") return (Math.round(n / 1e9) || 0).toLocaleString("vi-VN");  // || 0: a small loss rounds to 0, not -0
  if (kind === "vnd") return `${Math.round(n).toLocaleString("vi-VN")} đ`;
  if (kind === "days") return `${Math.round(n).toLocaleString("vi-VN")} ngày`;
  const places = key && TWO.has(key) ? 2 : 1;
  if (kind === "x") return `${n.toLocaleString("vi-VN", { minimumFractionDigits: places, maximumFractionDigits: places })}x`;
  const pct = (n * 100).toLocaleString("vi-VN", { minimumFractionDigits: places, maximumFractionDigits: places });
  return `${key && SIGNED.has(key) && n > 0 ? "+" : ""}${pct}%`;
}

export function periodLabel(p: string): string {
  return p.includes("-Q") ? `Q${p.slice(-1)}/${p.slice(2, 4)}` : p;
}

/** Indexes of the last n periods (all of them when n is 0). */
export function lastN<T>(periods: T[], n: number): number[] {
  const start = n === 0 ? 0 : Math.max(0, periods.length - n);
  return periods.map((_, i) => i).slice(start);
}

/** One line per period, newest first: every check that failed there with its two figures in tỷ đồng. */
/** Notes under the fixed-asset group: lines not synced yet, and periods with a finance lease (no line of its own). */
export function fixedNotes(d: { fixed_assets_pending?: boolean; finance_lease?: string[] }): string[] {
  const out: string[] = [];
  if (d.fixed_assets_pending) out.push("Chưa đồng bộ dòng tài sản cố định, chi phí trả trước, lợi thế thương mại, nợ vay, vốn chủ sở hữu, thuế TNDN và trái phiếu chuyển đổi: các dòng này để trống đến lượt 20:00 lấy lại lịch sử của mã này.");
  if (d.finance_lease?.length) out.push(`Có TSCĐ thuê tài chính (không có dòng riêng) ở ${d.finance_lease.map(periodLabel).join(", ")}.`);
  return out;
}

export function checkLines(checks: Check[]): string[] {
  const by = new Map<string, Check[]>();
  for (const c of checks) by.set(c.period, [...(by.get(c.period) ?? []), c]);
  return [...by.keys()].sort().reverse().map((p) => `${periodLabel(p)} · ${by.get(p)!
    .map((c) => `${c.label} (${c.a === null ? "—" : cell(c.a, "money", null)} so với ${c.b === null ? "—" : cell(c.b, "money", null)} tỷ)`).join("; ")}`);
}

const tone = (v: string | null, key: string | null) => (v !== null && key && SIGNED.has(key) ? (Number(v) > 0 ? "positive" : Number(v) < 0 ? "negative" : "") : "");
const ty = (v: string | null) => (v === null ? "—" : `${cell(v, "money", null)} tỷ`);

type Extra = { label: string; values: Record<string, string | null> } | null;  // the owner's forecast column, shown after the last quarter

/** Trung vị ngành: general companies (26/11/2026), banks, securities firms (ICB level 4 Dịch vụ đầu tư) and insurers (27/11/2026). */
export function showsSector(kind: Ratios["kind"] | undefined): boolean {
  return kind === "general" || kind === "bank" || kind === "securities" || kind === "insurance";
}

/** The caption line under the table for the Trung vị ngành column; null when the column is not shown. */
export function sectorNote(r: { kind: Ratios["kind"]; sector?: Sector | null }): string | null {
  if (!showsSector(r.kind) || !r.sector) return null;
  const q = periodLabel(`${r.sector.quarter.slice(0, 4)}-Q${Math.floor((Number(r.sector.quarter.slice(5, 7)) - 1) / 3) + 1}`);
  return `Trung vị ngành: trung vị của ${r.sector.peers} doanh nghiệp cùng ngành ${r.sector.name} (ICB cấp ${r.kind === "securities" ? 4 : 2}, HOSE) có số ở quý ${q}, không gồm mã này;`
    + ` cần ít nhất 3 doanh nghiệp, không thì để —${r.kind === "bank" ? "; CASA và tỷ lệ nợ nhóm 2 không có trung vị (chỉ có cho ngân hàng đang theo dõi)" : ""}${r.kind === "insurance"
      ? "; nhóm gồm cả bảo hiểm nhân thọ (BVH) và phi nhân thọ, tỷ lệ kết hợp và biên lợi nhuận khó so trực tiếp" : ""};`
    + " cao hơn hay thấp hơn trung vị không có nghĩa là tốt hay xấu.";
}

export function sectorColumn(s: Sector | null | undefined): Extra {
  if (!s) return null;
  const q = `${s.quarter.slice(0, 4)}-Q${Math.floor((Number(s.quarter.slice(5, 7)) - 1) / 3) + 1}`;
  return { label: `Trung vị ngành ${periodLabel(q)}`, values: s.medians };
}

function Table({ part, cols, caption, extra = null, sector = null, picked, onPick }: { part: Part; cols: number[]; caption: string; extra?: Extra; sector?: Extra; picked: string[];
  onPick: (key: string) => void }) {
  return (
    <div className="pb-scroll">
      <table className="pb-table ft-table">
        <caption className="caption">{caption}</caption>
        <thead><tr><th>Tỷ đồng</th>{cols.map((i) => <th key={part.periods[i]} className="num">{periodLabel(part.periods[i])}</th>)}
          {extra && <th className="num ft-forecast">{extra.label}</th>}{sector && <th className="num">{sector.label}</th>}<th>Xu hướng</th></tr></thead>
        <tbody>{part.rows.map((r, k) => r.kind === "group"
          ? <tr key={`g${k}`} className="ft-group"><th colSpan={cols.length + 2 + (extra ? 1 : 0) + (sector ? 1 : 0)}>{r.label}</th></tr>
          : <tr key={r.key ?? k} className={r.key && picked.includes(r.key) ? "ft-picked" : undefined}><td className={r.indent ? "ft-indent" : undefined}>
            {r.key ? <>
              {/* The label is a mouse shortcut; the icon button is the keyboard and screen-reader way to the same toggle. */}
              <span className="ft-label" onClick={() => onPick(r.key!)}>{r.label}</span>
              <button type="button" className="ft-pick" aria-pressed={picked.includes(r.key)} aria-label={`Vẽ biểu đồ: ${seriesName(part.rows, r.key)}`}
                title="Vẽ dòng này trên biểu đồ" onClick={() => onPick(r.key!)}><ChartColumn size={13} aria-hidden="true" /></button>
            </> : r.label}</td>
            {cols.map((i) => <td key={part.periods[i]} className={`num ${tone(r.values[i], r.key)}`}>{cell(r.values[i], r.kind, r.key)}</td>)}
            {extra && <td className={`num ft-forecast ${tone(extra.values[r.key ?? ""] ?? null, r.key)}`}>{cell(extra.values[r.key ?? ""] ?? null, r.kind, r.key)}</td>}
            {sector && <td className="num">{r.key && r.key in sector.values ? cell(sector.values[r.key] ?? null, r.kind, r.key) : ""}</td>}
            <td className="ft-spark"><Spark row={r} cols={cols} /></td></tr>)}</tbody>
      </table>
    </div>
  );
}

const FINANCIAL = new Set(["bank", "securities", "insurance"]);

/** A bank's, securities firm's or insurer's quarters with its sector ratios (VNDirect) as the first group, over the quarters of both;
 * a quarter one side lacks stays blank. */
export function withRatios(part: Part, ratios: Ratios): Part {
  const own = ratios.quarters.map((q) => `${q.date.slice(0, 4)}-Q${Math.floor((Number(q.date.slice(5, 7)) - 1) / 3) + 1}`);
  const periods = [...new Set([...part.periods, ...own])].sort();
  const at = (from: string[], values: (string | null)[]) => periods.map((p) => { const i = from.indexOf(p); return i < 0 ? null : values[i] ?? null; });
  const title = ratios.kind === "general" ? "Chỉ số tài chính (VNDirect)" : `Chỉ số ${TITLE[ratios.kind]}`;
  const rowKind = (f: Ratios["metrics"][number]["format"]) => (f === "times" ? "x" as const : f === "days" ? "days" as const : "pct" as const);
  const ratioRows: Row[] = [{ key: null, label: title, kind: "group", indent: 0, values: [] },
    ...ratios.metrics.map((m) => ({ key: m.code, label: m.label, kind: rowKind(m.format), indent: 0, values: at(own, m.values) }))];
  return { periods, rows: [...ratioRows, ...part.rows.map((r) => (r.kind === "group" ? r : { ...r, values: at(part.periods, r.values) }))] };
}

const PICKED: Record<string, string[]> = { insurance: ["ins_result", "fin_profit"], bank: ["pb", "roe"], securities: ["pb", "roe"] };

/** Bảng số tài chính: a non-financial company's statements, or a bank's, securities firm's or insurer's sector ratios with its scale
 * and valuation block, with the same chart, period buttons and table. */
export function FinancialTables({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Tables | null>(null);
  const [ratios, setRatios] = useState<Ratios | null>(null);
  const [ratioError, setRatioError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"quarters" | "years">("quarters");
  const [count, setCount] = useState<(typeof COUNTS)[number]>(8);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [picked, setPicked] = useState<string[]>(["revenue", "gross_margin"]);
  useEffect(() => {
    const sym = encodeURIComponent(symbol);
    api<Tables>(`fairvalue/statements/${sym}`).then((d) => {
      if (d.kind && FINANCIAL.has(d.kind)) {
        setPicked(PICKED[d.kind]);
        api<Ratios>(`fairvalue/ratios/${sym}`).then(setRatios, (e) => setRatioError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
      } else {
        api<Forecast>(`quarter-forecast/${sym}`).then(setForecast, () => setForecast(null));
        // Chỉ số tài chính (VNDirect): shown when the ticker's ratios are stored; none is no error, the table stays as it was
        api<Ratios>(`fairvalue/ratios/${sym}`).then(setRatios, () => setRatios(null));
      }
      setData(d);
    }, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted fx-loading" role="status">Đang tải bảng số…</p>;
  const financial = FINANCIAL.has(data.kind ?? "");
  if (data.reason && !(financial && ratios)) return <p className="muted">Chưa có bảng số tài chính: {data.reason}.</p>;
  const part = view === "quarters" && ratios ? withRatios(data.quarters, ratios) : data[view];
  const cols = view === "quarters" ? lastN(part.periods, count) : lastN(part.periods, 0);
  const s = data.summary;
  const pe = (data as { pe_context?: PeContext | null }).pe_context ?? null;
  const note = peNote(pe), calm = peCalm(pe);
  const flags = (data as { flags?: { outside_sales: OutsideSales; eps: { nam: string }[] } | null }).flags ?? null;
  const outside = outsideSalesNote(flags?.outside_sales ?? null), epsWarn = epsNote(flags?.eps);
  const own = historyCards((data as { own_history?: OwnHistory }).own_history ?? null);
  const extra = view === "quarters" && forecast?.quarter && Object.keys(forecast.values).length ? { label: `${periodLabel(forecast.quarter)}F`, values: forecast.values } : null;
  return (
    <div className="ft">
      {note && <p className="notice" data-testid="pe-context">{note}</p>}
      {calm && <p className="caption" data-testid="pe-context">{calm}</p>}
      {outside && <p className="notice" data-testid="report-flags">{outside}</p>}
      {epsWarn && <p className="notice" data-testid="report-flags">{epsWarn}</p>}
      {s && <div className="pb-cards" aria-label="Bốn quý gần nhất">
        <div><span className="caption">LNST công ty mẹ 4 quý ({s.quarters.map(periodLabel).join(", ")})</span><strong>{ty(s.npat_ttm)}</strong></div>
        <div><span className="caption">EBITDA 4 quý</span><strong>{ty(s.ebitda_ttm)}</strong></div>
        <div><span className="caption">ROE 4 quý</span><strong>{cell(s.roe, "pct", null)}</strong></div>
        <div title="LN HĐKD lõi 4 quý × (1 − thuế thực tế) ÷ vốn đầu tư bình quân (vốn chủ gồm cổ đông thiểu số + vay − tiền và đầu tư ngắn hạn), đầu và cuối 4 quý">
          <span className="caption">ROIC vận hành 4 quý</span><strong>{cell(s.roic ?? null, "pct", null)}</strong></div>
        <div><span className="caption">P/E · P/B · EV/EBITDA {s.close_date ? `(giá ${s.close_date.split("-").reverse().join("/")})` : ""}</span>
          <strong>{cell(s.pe, "x", null)} · {cell(s.pb, "x", null)} · {cell(s.ev_ebitda, "x", null)}</strong></div>
        {own.map((o) => <div key={o.title} title="Tự tính mỗi cuối tháng: vốn hóa (giá chưa điều chỉnh × số cổ phiếu của quý đã công bố, cộng các đợt thưởng sau quý) ÷ LNST công ty mẹ 4 quý hoặc vốn chủ công ty mẹ; trung vị, không dùng trung bình">
          <span className="caption">{o.title}</span><strong>{o.value}</strong>{o.sub && <span className="caption">{o.sub}</span>}</div>)}
      </div>}
      <div className="pb-head">
        <span className="pb-toggle" role="radiogroup" aria-label="Kỳ">{(["quarters", "years"] as const).map((v) =>
          <button key={v} type="button" role="radio" aria-checked={view === v} className={`btn ${view === v ? "primary" : ""}`} onClick={() => setView(v)}>
            {v === "quarters" ? "Quý" : "Năm"}</button>)}</span>
        {view === "quarters" && <span className="pb-toggle" role="group" aria-label="Số quý">{COUNTS.map((n) =>
          <button key={n} type="button" className={`btn ${count === n ? "primary" : ""}`} aria-pressed={count === n} onClick={() => setCount(n)}>
            {n === 0 ? "Tất cả" : `${n} quý`}</button>)}</span>}
      </div>
      {financial && view === "years" && <p className="caption">Chỉ số {TITLE[data.kind as Kind]} chỉ có theo quý; chế độ Năm chỉ có Quy mô và định giá.</p>}
      {ratioError && <p className="errors" role="alert">Chưa có chỉ số {TITLE[data.kind as Kind]}: {ratioError}</p>}
      {part.periods.length === 0 ? <p className="muted">Chưa có kỳ nào.</p>
        : <>
          <StatementChart rows={part.rows} periods={part.periods} cols={cols} keys={picked} forecast={extra} checks={data.checks}
            onRemove={(key) => setPicked((p) => p.filter((k) => k !== key))} />
          <Table part={part} cols={cols} caption={`${view === "quarters" ? `${cols.length} quý, cũ bên trái` : `${cols.length} năm`} · bấm tên dòng để vẽ (tối đa 2 dòng)`}
            extra={extra} sector={view === "quarters" && showsSector(ratios?.kind) ? sectorColumn(ratios?.sector) : null} picked={picked} onPick={(key) => setPicked((p) => toggleRow(p, key))} />
        </>}
      {!financial && fixedNotes(data).map((n) => <p key={n} className="caption" data-testid="fixed-notes">{n}</p>)}
      {!financial && view === "quarters" && forecast && <ForecastForm key={`${forecast.quarter}-${forecast.version}`} symbol={symbol} data={forecast} onSaved={setForecast} />}
      {data.valuation_check && <details className="mc-table" aria-label="Đối chiếu định giá">
        <summary>Đối chiếu định giá với VNDirect: {data.valuation_check.flagged ? `${data.valuation_check.flagged} chỉ tiêu lệch hơn 10%` : "không lệch quá 10%"}</summary>
        <div className="tablewrap"><table aria-label="Đối chiếu định giá với VNDirect">
          <thead><tr><th>Chỉ tiêu</th><th className="num">Phần mềm</th><th className="num">VNDirect</th><th className="num">Lệch</th></tr></thead>
          <tbody>{data.valuation_check.rows.map((r) => <tr key={r.key}><td>{r.label}</td>
            <td className="num">{r.ours === null ? "—" : r.key === "market_cap" ? ty(r.ours) : cell(r.ours, "x", null)}</td>
            <td className="num">{r.theirs === null ? "—" : r.key === "market_cap" ? ty(r.theirs) : cell(r.theirs, "x", null)}</td>
            <td className={`num ${r.off ? "negative" : ""}`}>{r.diff === null ? "—" : `${(Number(r.diff) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`}</td></tr>)}</tbody>
        </table></div>
        {data.valuation_check.rows.filter((r) => r.note).map((r) => <p key={r.key} className="notice">{r.label}: {r.note}</p>)}
        <p className="caption">Phần mềm tính theo giá đóng cửa mới nhất đã lưu{data.valuation_check.ours_date ? ` (${data.valuation_check.ours_date.split("-").reverse().join("/")})` : ""}, VNDirect theo số của họ{data.valuation_check.date ? ` (${data.valuation_check.date.split("-").reverse().join("/")})` : ""}. Hai bên có thể khác cách tính lợi nhuận và số cổ phiếu; lệch hơn 10% thì nên xem lại, phần mềm không tự chỉnh số.{data.valuation_check.shares_from_vndirect && " Mã này: vốn hoá tính theo số cổ phiếu cuối quý lệch hơn 10%, nên phần mềm dùng số cổ phiếu hiện tại của VNDirect, vì vậy hai bên gần như trùng và không còn là phép kiểm tra độc lập."}</p>
      </details>}
      {(data.checks.length > 0 || data.conflicts.length > 0) && <details className="mc-table">
        <summary>Kiểm tra chéo: {data.checks.length} chỗ lệch hơn 0,5% ở {new Set(data.checks.map((c) => c.period)).size} kỳ{data.conflicts.length ? `, ${data.conflicts.length} dòng nguồn ghi hai số` : ""}</summary>
        <ul className="ft-checks">
          {checkLines(data.checks).map((line) => <li key={line}>{line}</li>)}
          {data.conflicts.map((c) => <li key={`${c.period}-${c.line}`}>{periodLabel(c.period)} · dòng {c.line}: nguồn ghi {c.values.map(ty).join(" và ")}, không lấy số nào</li>)}
        </ul>
      </details>}
      {ratios?.notes && ratios.notes.length > 0 && <details className="mc-table">
        <summary>Đối chiếu nợ nhóm 2, CASA và CAR: {ratios.notes.length} ghi chú</summary>
        <ul className="ft-checks">{ratios.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      </details>}
      {financial ? <p className="caption wrap">
        {ratios && sectorNote(ratios) && <>{sectorNote(ratios)} </>}
        Chỉ số {TITLE[data.kind as Kind]}: tỷ lệ VNDirect tính sẵn (dữ liệu công khai, từ Q4/2017; ROAA, ROAE từ Q3/2023), chỉ có theo quý; NIM, ROAA, ROAE,
        biên lợi nhuận trên 4–5 quý gần nhất, các tỷ lệ khác tại cuối quý; ô — là quý nguồn chưa có số.{data.kind === "bank" ? ` Tỷ lệ nợ nhóm 2 = nợ nhóm 2 / nợ nhóm 1–5 và CASA = (tiền gửi không kỳ hạn + ký quỹ) / tiền gửi của khách hàng: từ thuyết minh báo cáo tài chính trên API công khai của Vietcap (từ Q1/2018${ratios?.notes_fetched_at ? `, đọc ${new Date(ratios.notes_fetched_at).toLocaleDateString("vi-VN")}` : ""}), chỉ ở quý mà các nhóm nợ và các loại tiền gửi cộng ra đúng tổng; quý đã nhập ở Số liệu ngân hàng (nhập tay) dùng số nhập tay. CAR (cuối năm): tỷ lệ an toàn vốn cuối năm của Vietcap, ở cột Q4 (không nguồn miễn phí nào có CAR theo quý); năm Vietcap chưa có thì dùng số của VNDirect (trừ mức 8% giữ chỗ); hai nguồn lệch quá 0,1 điểm hoặc Vietcap trùng đúng năm trước thì ghi ở mục đối chiếu. Thiếu thì để trống, không nội suy.` : ""} Quy mô và định giá: báo cáo tài chính trên API công
        khai của VNDirect{data.fetched_at ? `, đọc ${new Date(data.fetched_at).toLocaleDateString("vi-VN")}` : ""}. Vốn hoá = giá đóng
        cửa thực (chưa điều chỉnh) phiên cuối kỳ × số cổ phiếu cuối kỳ (vốn góp ÷ 10.000 đ); giá thực có từ 2013. Vốn chủ công ty mẹ = vốn chủ sở hữu − lợi
        ích cổ đông không kiểm soát; giá trị sổ sách / cổ phiếu = vốn chủ công ty mẹ ÷ số cổ phiếu. Quý: P/E, ROE và các bội số theo lợi nhuận, thu nhập tính
        trên 4 quý tới quý đó (thiếu một quý thì để trống); năm: số cả năm. ROE = LNST công ty mẹ ÷ vốn chủ công ty mẹ bình quân kỳ đó và cùng kỳ năm
        trước, nên có thể lệch ROAE của VNDirect ở nhóm chỉ số. {data.kind === "bank" ? "LN trước dự phòng = lợi nhuận thuần từ hoạt động kinh doanh trước chi phí dự phòng rủi ro tín dụng."
          : data.kind === "securities" ? "Vay = vay và nợ ngắn hạn + dài hạn, trên vốn chủ sở hữu (cả phần không kiểm soát)."
          : "Danh mục đầu tư = tiền + đầu tư tài chính ngắn hạn + dài hạn, trên vốn chủ sở hữu (cả phần không kiểm soát). Kết quả kinh doanh bảo hiểm = lợi nhuận thuần từ hoạt động kinh doanh bảo hiểm; với bảo hiểm nhân thọ thường âm vì khoản tăng dự phòng toán học ghi vào chi phí và được bù bằng lãi đầu tư, không có nghĩa là lỗ. Chỉ hiện ở kỳ mà kết quả bảo hiểm, lợi nhuận hoạt động tài chính và các khoản khác cộng ra đúng LNTT (từ giữa 2014; mẫu báo cáo cũ không cộng ra được, để trống và ghi ở Kiểm tra chéo). Không tính P/EV: giá trị nội tại không có trong báo cáo tài chính. Tỷ lệ kết hợp là số của VNDirect ở nhóm chỉ số."} Không
        tính nợ ròng, EV, EBITDA, FCFF: với ngân hàng, công ty chứng khoán và bảo hiểm, đi vay hay giữ tiền của khách là hoạt động kinh doanh. Thiếu một thành phần thì để trống, không ước lượng.
      </p> : <p className="caption wrap">
        {ratios?.kind === "general" && <>Chỉ số tài chính (VNDirect): tỷ lệ VNDirect tính sẵn từ dữ liệu công khai{ratios.fetched_at ? `, đọc ${new Date(ratios.fetched_at).toLocaleDateString("vi-VN")}` : ""},
          chỉ có theo quý; ROAE, ROAA, ROIC, biên lợi nhuận, dòng tiền / doanh thu và khả năng trả lãi trên 4–5 quý gần nhất, các hệ số khác tại cuối quý;
          quý doanh thu rất nhỏ làm số ngày và biên lệch xa, giữ nguyên như nguồn; có thể lệch ROE 4 quý và ROIC vận hành ở trên vì ứng dụng tự tính từ
          báo cáo tài chính; ô — là quý nguồn chưa có số. </>}
        {ratios && sectorNote(ratios) && <>{sectorNote(ratios)} </>}
        Nguồn: báo cáo tài chính trên API công khai của VNDirect{data.fetched_at ? `, đọc ${new Date(data.fetched_at).toLocaleDateString("vi-VN")}` : ""}; số từng quý (không lũy kế),
        chi phí ghi số âm. LN HĐKD lõi = lãi gộp − chi phí bán hàng − quản lý. EBIT = LNTT + lãi vay; EBITDA = EBIT + khấu hao. FCFF = lưu chuyển tiền
        HĐKD + lãi vay × (1 − thuế ÷ LNTT) + capex; không tính khi LNTT ≤ 0. Vốn hoá năm = giá đóng cửa thực (chưa điều chỉnh) phiên cuối năm × số cổ
        phiếu cuối năm (vốn góp ÷ 10.000 đ); giá thực có từ 2013, năm trước đó để trống; vốn hoá quý tương tự theo phiên cuối quý và số cổ
        phiếu cuối quý, còn P/E, EV/EBITDA, EV/doanh thu, lợi suất FCFF và ROE của quý tính trên 4 quý tới quý đó (thiếu một quý thì để trống); vốn hoá ở thẻ 4 quý theo giá gần nhất × số cổ phiếu hiện tại; nợ ròng = nợ vay
        ngắn + dài hạn − tiền − đầu tư tài chính ngắn hạn; EV = vốn hoá + nợ ròng + lợi ích cổ đông không kiểm soát; P/B trên vốn chủ của công ty mẹ;
        ROE = LNST công ty mẹ ÷ vốn chủ bình quân đầu và cuối kỳ. Thiếu một thành phần thì để trống, không ước lượng. Kiểm tra chéo: lãi gộp với doanh thu
        − giá vốn, tổng 4 quý với cả năm, LNST với nguồn Vnstock, giá trị còn lại với nguyên giá + hao mòn lũy kế; dòng tiền quý những năm cũ thường lệch số cả năm đã kiểm toán.
        Tài sản cố định: số dư cuối kỳ (không cộng 4 quý). Mức hao mòn = hao mòn lũy kế ÷ nguyên giá TSCĐ hữu hình: tài sản đã cũ đến đâu.
        XDCB ÷ TSCĐ hữu hình = chi phí xây dựng cơ bản dở dang ÷ TSCĐ hữu hình còn lại: phần tài sản sắp hình thành; khi dự án xong, XDCB kết
        chuyển sang nguyên giá và khấu hao sẽ tăng. Capex ÷ khấu hao lớn hơn 1: đang đầu tư nhiều hơn phần hao mòn. Vòng quay TSCĐ hữu hình =
        doanh thu thuần ÷ TSCĐ hữu hình còn lại bình quân đầu và cuối kỳ. Quý: hai tỷ lệ sau tính trên 4 quý tới quý đó. VNDirect chỉ có số dư,
        không có số phát sinh tăng, giảm của thuyết minh, nên phần mềm không tính số kết chuyển.
        Chi phí trả trước: chi phí đã trả tiền nhưng ghi thành tài sản, phân bổ dần vào chi phí các kỳ sau (không tốn thêm tiền khi phân bổ); ÷ LNTT là LNTT
        của kỳ (quý: 4 quý). Tăng, giảm chi phí trả trước lấy từ lưu chuyển tiền tệ, chỉ phần vận hành, nên có thể khác chênh lệch số dư. VNDirect không có số phân bổ trong năm.
        Lợi thế thương mại: phần trả cao hơn tài sản thuần khi mua công ty, phân bổ dần tối đa 10 năm; dòng phân bổ của VNDirect thường để trống. P/B loại lợi thế
        thương mại = vốn hoá ÷ (vốn chủ công ty mẹ − lợi thế thương mại); không trừ TSCĐ vô hình vì ở Việt Nam phần lớn là quyền sử dụng đất.
        Nợ vay: lãi suất vay bình quân = chi phí lãi vay ÷ nợ vay bình quân cuối kỳ và cùng kỳ năm trước; khả năng trả lãi = EBIT ÷ lãi vay (quý: 4 quý). Vay thuần =
        tiền vay nhận được + tiền trả nợ gốc. Lãi suất từng khoản, loại tiền, nợ dài hạn đến hạn trả chỉ có trong thuyết minh.
        Biên gộp so với trung bình 4 năm trước: biên gộp kỳ đó trừ trung bình biên gộp của cùng kỳ 4 năm trước (quý: 4 quý tới quý đó); lệch nhiều thì đọc
        thuyết minh giá vốn. Giảm trừ ÷ doanh thu bán hàng: chiết khấu, giảm giá, hàng bán bị trả lại. Chi phí tài chính ngoài lãi vay: lỗ tỷ giá, dự phòng
        đầu tư, lỗ thanh lý. Tiền thu lãi, cổ tức ÷ doanh thu tài chính: phần đã thu bằng tiền (lãi tỷ giá, lãi thanh lý thu tiền ở dòng khác).
        Vốn chủ sở hữu: vốn chủ công ty mẹ ÷ vốn góp dưới 1 là đã mất một phần vốn góp. Thay đổi vốn chủ ngoài lợi nhuận = vốn chủ cuối kỳ − kỳ trước (quý: quý liền
        trước) − LNST − tiền phát hành − tiền mua lại cổ phiếu + cổ tức đã trả: thoái vốn công ty con, điều chỉnh hồi tố, chênh lệch tỷ giá, trích quỹ…; số lớn thì đọc thuyết minh thay đổi vốn chủ.
        Thuế TNDN: thuế suất thực tế = chi phí thuế ÷ LNTT (quý: 4 quý), thường khác 20% vì ưu đãi thuế, chi phí không được trừ, chuyển lỗ; thuế hoãn lại âm là lợi
        ích thuế. Thuế đã nộp ÷ chi phí thuế: phần thuế của kỳ đã nộp bằng tiền.
        Trên mỗi cổ phiếu: EPS cơ bản là số doanh nghiệp công bố, không điều chỉnh lại khi sau đó có cổ phiếu thưởng (so các năm cũ cần chú ý); EPS báo cáo ÷ phần
        tự tính thấp hơn 1 khi trừ quỹ khen thưởng, phúc lợi hoặc có phát hành trong kỳ (số cổ phiếu bình quân gia quyền).
      </p>}
    </div>
  );
}
