"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Row = { key: string | null; label: string; kind: "group" | "money" | "pct" | "x"; indent: number; values: (string | null)[] };
type Part = { periods: string[]; rows: Row[] };
type Check = { period: string; check: string; label: string; a: string | null; b: string | null };
type Conflict = { period: string; line: string; values: string[] };
type Summary = { period: string; close_date: string | null; market_cap: string | null; npat_ttm: string | null; ebitda_ttm: string | null;
  ev: string | null; pe: string | null; pb: string | null; ev_ebitda: string | null; roe: string | null; quarters: string[] };
type Tables = { symbol: string; reason: string | null; source?: string; fetched_at?: string; quarters: Part; years: Part; summary: Summary | null;
  checks: Check[]; conflicts: Conflict[] };

const SIGNED = new Set(["revenue_yoy", "gross_profit_yoy", "npat_parent_yoy", "ebitda_yoy", "fcff_yield"]);
const COUNTS = [8, 12, 20, 0] as const;

export function cell(v: string | null, kind: Row["kind"], key: string | null): string {
  if (v === null) return "—";
  const n = Number(v);
  if (kind === "money") return (Math.round(n / 1e9) || 0).toLocaleString("vi-VN");  // || 0: a small loss rounds to 0, not -0
  if (kind === "x") return `${n.toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}x`;
  const pct = (n * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
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
export function checkLines(checks: Check[]): string[] {
  const by = new Map<string, Check[]>();
  for (const c of checks) by.set(c.period, [...(by.get(c.period) ?? []), c]);
  return [...by.keys()].sort().reverse().map((p) => `${periodLabel(p)} · ${by.get(p)!
    .map((c) => `${c.label} (${c.a === null ? "—" : cell(c.a, "money", null)} so với ${c.b === null ? "—" : cell(c.b, "money", null)} tỷ)`).join("; ")}`);
}

const tone = (v: string | null, key: string | null) => (v !== null && key && SIGNED.has(key) ? (Number(v) > 0 ? "positive" : Number(v) < 0 ? "negative" : "") : "");
const ty = (v: string | null) => (v === null ? "—" : `${cell(v, "money", null)} tỷ`);

function Table({ part, cols, caption }: { part: Part; cols: number[]; caption: string }) {
  return (
    <div className="pb-scroll">
      <table className="pb-table ft-table">
        <caption className="caption">{caption}</caption>
        <thead><tr><th>Tỷ đồng</th>{cols.map((i) => <th key={part.periods[i]} className="num">{periodLabel(part.periods[i])}</th>)}</tr></thead>
        <tbody>{part.rows.map((r, k) => r.kind === "group"
          ? <tr key={`g${k}`} className="ft-group"><th colSpan={cols.length + 1}>{r.label}</th></tr>
          : <tr key={r.key ?? k}><td className={r.indent ? "ft-indent" : undefined}>{r.label}</td>
            {cols.map((i) => <td key={part.periods[i]} className={`num ${tone(r.values[i], r.key)}`}>{cell(r.values[i], r.kind, r.key)}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export function FinancialTables({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Tables | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"quarters" | "years">("quarters");
  const [count, setCount] = useState<(typeof COUNTS)[number]>(8);
  useEffect(() => {
    api<Tables>(`fairvalue/statements/${encodeURIComponent(symbol)}`).then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted fx-loading" role="status">Đang tải bảng số…</p>;
  if (data.reason) return <p className="muted">Chưa có bảng số tài chính: {data.reason}.</p>;
  const part = data[view];
  const cols = view === "quarters" ? lastN(part.periods, count) : lastN(part.periods, 0);
  const s = data.summary;
  return (
    <div className="ft">
      {s && <div className="pb-cards" aria-label="Bốn quý gần nhất">
        <div><span className="caption">LNST công ty mẹ 4 quý ({s.quarters.map(periodLabel).join(", ")})</span><strong>{ty(s.npat_ttm)}</strong></div>
        <div><span className="caption">EBITDA 4 quý</span><strong>{ty(s.ebitda_ttm)}</strong></div>
        <div><span className="caption">ROE 4 quý</span><strong>{cell(s.roe, "pct", null)}</strong></div>
        <div><span className="caption">P/E · P/B · EV/EBITDA {s.close_date ? `(giá ${s.close_date.split("-").reverse().join("/")})` : ""}</span>
          <strong>{cell(s.pe, "x", null)} · {cell(s.pb, "x", null)} · {cell(s.ev_ebitda, "x", null)}</strong></div>
      </div>}
      <div className="pb-head">
        <span className="pb-toggle" role="radiogroup" aria-label="Kỳ">{(["quarters", "years"] as const).map((v) =>
          <button key={v} type="button" role="radio" aria-checked={view === v} className={`btn ${view === v ? "primary" : ""}`} onClick={() => setView(v)}>
            {v === "quarters" ? "Quý" : "Năm"}</button>)}</span>
        {view === "quarters" && <span className="pb-toggle" role="group" aria-label="Số quý">{COUNTS.map((n) =>
          <button key={n} type="button" className={`btn ${count === n ? "primary" : ""}`} aria-pressed={count === n} onClick={() => setCount(n)}>
            {n === 0 ? "Tất cả" : `${n} quý`}</button>)}</span>}
      </div>
      {part.periods.length === 0 ? <p className="muted">Chưa có kỳ nào.</p>
        : <Table part={part} cols={cols} caption={view === "quarters" ? `${cols.length} quý, cũ bên trái` : `${cols.length} năm`} />}
      {(data.checks.length > 0 || data.conflicts.length > 0) && <details className="mc-table">
        <summary>Kiểm tra chéo: {data.checks.length} chỗ lệch hơn 0,5% ở {new Set(data.checks.map((c) => c.period)).size} kỳ{data.conflicts.length ? `, ${data.conflicts.length} dòng nguồn ghi hai số` : ""}</summary>
        <ul className="ft-checks">
          {checkLines(data.checks).map((line) => <li key={line}>{line}</li>)}
          {data.conflicts.map((c) => <li key={`${c.period}-${c.line}`}>{periodLabel(c.period)} · dòng {c.line}: nguồn ghi {c.values.map(ty).join(" và ")}, không lấy số nào</li>)}
        </ul>
      </details>}
      <p className="caption wrap">
        Nguồn: báo cáo tài chính trên API công khai của VNDirect{data.fetched_at ? `, đọc ${new Date(data.fetched_at).toLocaleDateString("vi-VN")}` : ""}; số từng quý (không lũy kế),
        chi phí ghi số âm. LN HĐKD lõi = lãi gộp − chi phí bán hàng − quản lý. EBIT = LNTT + lãi vay; EBITDA = EBIT + khấu hao. FCFF = lưu chuyển tiền
        HĐKD + lãi vay × (1 − thuế ÷ LNTT) + capex; không tính khi LNTT ≤ 0. Vốn hoá năm = giá đóng cửa thực (chưa điều chỉnh) phiên cuối năm × số cổ
        phiếu cuối năm (vốn góp ÷ 10.000 đ); giá thực có từ 2013, năm trước đó để trống; vốn hoá 4 quý theo giá gần nhất × số cổ phiếu hiện tại; nợ ròng = nợ vay
        ngắn + dài hạn − tiền − đầu tư tài chính ngắn hạn; EV = vốn hoá + nợ ròng + lợi ích cổ đông không kiểm soát; P/B trên vốn chủ của công ty mẹ;
        ROE = LNST công ty mẹ ÷ vốn chủ bình quân đầu và cuối kỳ. Thiếu một thành phần thì để trống, không ước lượng. Kiểm tra chéo: lãi gộp với doanh thu
        − giá vốn, tổng 4 quý với cả năm, LNST với nguồn Vnstock; dòng tiền quý những năm cũ thường lệch số cả năm đã kiểm toán.
      </p>
    </div>
  );
}
