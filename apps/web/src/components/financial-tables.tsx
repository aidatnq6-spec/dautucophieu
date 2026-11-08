"use client";
import { useEffect, useState } from "react";
import { ChartColumn } from "lucide-react";
import { ApiError, api } from "../lib/api";
import { type Forecast, ForecastForm } from "./quarter-forecast";
import { Spark, StatementChart, seriesName, toggleRow } from "./statement-chart";

type Row = { key: string | null; label: string; kind: "group" | "money" | "pct" | "x" | "vnd"; indent: number; values: (string | null)[] };
type Part = { periods: string[]; rows: Row[] };
type Check = { period: string; check: string; label: string; a: string | null; b: string | null };
type Conflict = { period: string; line: string; values: string[] };
type Summary = { period: string; close_date: string | null; market_cap: string | null; npat_ttm: string | null; ebitda_ttm: string | null;
  ev: string | null; pe: string | null; pb: string | null; ev_ebitda: string | null; roe: string | null; quarters: string[] };
type Tables = { symbol: string; kind?: "bank" | "securities" | "insurance" | null; reason: string | null; source?: string; fetched_at?: string; quarters: Part; years: Part; summary: Summary | null;
  checks: Check[]; conflicts: Conflict[] };

const SIGNED = new Set(["revenue_yoy", "gross_profit_yoy", "npat_parent_yoy", "ebitda_yoy", "fcff_yield"]);
const COUNTS = [8, 12, 20, 0] as const;

export function cell(v: string | null, kind: Row["kind"], key: string | null): string {
  if (v === null) return "—";
  const n = Number(v);
  if (kind === "money") return (Math.round(n / 1e9) || 0).toLocaleString("vi-VN");  // || 0: a small loss rounds to 0, not -0
  if (kind === "vnd") return `${Math.round(n).toLocaleString("vi-VN")} đ`;
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

type Extra = { label: string; values: Record<string, string | null> } | null;  // the owner's forecast column, shown after the last quarter

function Table({ part, cols, caption, extra = null, picked, onPick }: { part: Part; cols: number[]; caption: string; extra?: Extra; picked: string[];
  onPick: (key: string) => void }) {
  return (
    <div className="pb-scroll">
      <table className="pb-table ft-table">
        <caption className="caption">{caption}</caption>
        <thead><tr><th>Tỷ đồng</th>{cols.map((i) => <th key={part.periods[i]} className="num">{periodLabel(part.periods[i])}</th>)}
          {extra && <th className="num ft-forecast">{extra.label}</th>}<th>Xu hướng</th></tr></thead>
        <tbody>{part.rows.map((r, k) => r.kind === "group"
          ? <tr key={`g${k}`} className="ft-group"><th colSpan={cols.length + 2 + (extra ? 1 : 0)}>{r.label}</th></tr>
          : <tr key={r.key ?? k} className={r.key && picked.includes(r.key) ? "ft-picked" : undefined}><td className={r.indent ? "ft-indent" : undefined}>
            {r.key ? <>
              {/* The label is a mouse shortcut; the icon button is the keyboard and screen-reader way to the same toggle. */}
              <span className="ft-label" onClick={() => onPick(r.key!)}>{r.label}</span>
              <button type="button" className="ft-pick" aria-pressed={picked.includes(r.key)} aria-label={`Vẽ biểu đồ: ${seriesName(part.rows, r.key)}`}
                title="Vẽ dòng này trên biểu đồ" onClick={() => onPick(r.key!)}><ChartColumn size={13} aria-hidden="true" /></button>
            </> : r.label}</td>
            {cols.map((i) => <td key={part.periods[i]} className={`num ${tone(r.values[i], r.key)}`}>{cell(r.values[i], r.kind, r.key)}</td>)}
            {extra && <td className={`num ft-forecast ${tone(extra.values[r.key ?? ""] ?? null, r.key)}`}>{cell(extra.values[r.key ?? ""] ?? null, r.kind, r.key)}</td>}
            <td className="ft-spark"><Spark row={r} cols={cols} /></td></tr>)}</tbody>
      </table>
    </div>
  );
}

const FINANCIAL = new Set(["bank", "securities"]);

/** Bảng số tài chính of a non-financial company; with `financial`, the Quy mô và định giá block of a bank or securities firm, in its
 * own section (nothing for any other ticker). */
export function FinancialTables({ symbol, financial = false }: { symbol: string; financial?: boolean }) {
  const [data, setData] = useState<Tables | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"quarters" | "years">("quarters");
  const [count, setCount] = useState<(typeof COUNTS)[number]>(8);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [picked, setPicked] = useState<string[]>(financial ? ["pb", "roe"] : ["revenue", "gross_margin"]);
  useEffect(() => {
    api<Tables>(`fairvalue/statements/${encodeURIComponent(symbol)}`).then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
    if (!financial) api<Forecast>(`quarter-forecast/${encodeURIComponent(symbol)}`).then(setForecast, () => setForecast(null));
  }, [symbol, financial]);
  if (financial) {
    if (!data || !FINANCIAL.has(data.kind ?? "")) return null;
    return <section className="surface" aria-label="Quy mô và định giá"><h2>Quy mô và định giá</h2>{body(data)}</section>;
  }
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted fx-loading" role="status">Đang tải bảng số…</p>;
  if (FINANCIAL.has(data.kind ?? "")) return <p className="muted">Ngân hàng và công ty chứng khoán không dùng bảng này: xem khối Quy mô và định giá bên dưới, sau Chỉ số ngành theo quý.</p>;
  if (data.reason) return <p className="muted">Chưa có bảng số tài chính: {data.reason}.</p>;
  return body(data);

  function body(data: Tables) {
  if (financial && data.reason) return <p className="muted">Chưa có số: {data.reason}.</p>;
  const part = data[view];
  const cols = view === "quarters" ? lastN(part.periods, count) : lastN(part.periods, 0);
  const s = data.summary;
  const extra = view === "quarters" && forecast?.quarter && Object.keys(forecast.values).length ? { label: `${periodLabel(forecast.quarter)}F`, values: forecast.values } : null;
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
        : <>
          <StatementChart rows={part.rows} periods={part.periods} cols={cols} keys={picked} forecast={extra} checks={data.checks}
            onRemove={(key) => setPicked((p) => p.filter((k) => k !== key))} />
          <Table part={part} cols={cols} caption={`${view === "quarters" ? `${cols.length} quý, cũ bên trái` : `${cols.length} năm`} · bấm tên dòng để vẽ (tối đa 2 dòng)`}
            extra={extra} picked={picked} onPick={(key) => setPicked((p) => toggleRow(p, key))} />
        </>}
      {!financial && view === "quarters" && forecast && <ForecastForm key={`${forecast.quarter}-${forecast.version}`} symbol={symbol} data={forecast} onSaved={setForecast} />}
      {(data.checks.length > 0 || data.conflicts.length > 0) && <details className="mc-table">
        <summary>Kiểm tra chéo: {data.checks.length} chỗ lệch hơn 0,5% ở {new Set(data.checks.map((c) => c.period)).size} kỳ{data.conflicts.length ? `, ${data.conflicts.length} dòng nguồn ghi hai số` : ""}</summary>
        <ul className="ft-checks">
          {checkLines(data.checks).map((line) => <li key={line}>{line}</li>)}
          {data.conflicts.map((c) => <li key={`${c.period}-${c.line}`}>{periodLabel(c.period)} · dòng {c.line}: nguồn ghi {c.values.map(ty).join(" và ")}, không lấy số nào</li>)}
        </ul>
      </details>}
      {financial ? <p className="caption wrap">
        Nguồn: báo cáo tài chính trên API công khai của VNDirect{data.fetched_at ? `, đọc ${new Date(data.fetched_at).toLocaleDateString("vi-VN")}` : ""}. Vốn hoá = giá đóng
        cửa thực (chưa điều chỉnh) phiên cuối kỳ × số cổ phiếu cuối kỳ (vốn góp ÷ 10.000 đ); giá thực có từ 2013. Vốn chủ công ty mẹ = vốn chủ sở hữu − lợi
        ích cổ đông không kiểm soát; giá trị sổ sách / cổ phiếu = vốn chủ công ty mẹ ÷ số cổ phiếu. Quý: P/E, ROE và các bội số theo lợi nhuận, thu nhập tính
        trên 4 quý tới quý đó (thiếu một quý thì để trống); năm: số cả năm. ROE = LNST công ty mẹ ÷ vốn chủ công ty mẹ bình quân kỳ đó và cùng kỳ năm
        trước, nên có thể lệch ROAE của VNDirect ở bảng chỉ số. {data.kind === "bank" ? "LN trước dự phòng = lợi nhuận thuần từ hoạt động kinh doanh trước chi phí dự phòng rủi ro tín dụng." : "Vay = vay và nợ ngắn hạn + dài hạn, trên vốn chủ sở hữu (cả phần không kiểm soát)."} Không
        tính nợ ròng, EV, EBITDA, FCFF: với ngân hàng và công ty chứng khoán, đi vay là hoạt động kinh doanh. Thiếu một thành phần thì để trống, không ước lượng.
      </p> : <p className="caption wrap">
        Nguồn: báo cáo tài chính trên API công khai của VNDirect{data.fetched_at ? `, đọc ${new Date(data.fetched_at).toLocaleDateString("vi-VN")}` : ""}; số từng quý (không lũy kế),
        chi phí ghi số âm. LN HĐKD lõi = lãi gộp − chi phí bán hàng − quản lý. EBIT = LNTT + lãi vay; EBITDA = EBIT + khấu hao. FCFF = lưu chuyển tiền
        HĐKD + lãi vay × (1 − thuế ÷ LNTT) + capex; không tính khi LNTT ≤ 0. Vốn hoá năm = giá đóng cửa thực (chưa điều chỉnh) phiên cuối năm × số cổ
        phiếu cuối năm (vốn góp ÷ 10.000 đ); giá thực có từ 2013, năm trước đó để trống; vốn hoá quý tương tự theo phiên cuối quý và số cổ
        phiếu cuối quý, còn P/E, EV/EBITDA, EV/doanh thu, lợi suất FCFF và ROE của quý tính trên 4 quý tới quý đó (thiếu một quý thì để trống); vốn hoá ở thẻ 4 quý theo giá gần nhất × số cổ phiếu hiện tại; nợ ròng = nợ vay
        ngắn + dài hạn − tiền − đầu tư tài chính ngắn hạn; EV = vốn hoá + nợ ròng + lợi ích cổ đông không kiểm soát; P/B trên vốn chủ của công ty mẹ;
        ROE = LNST công ty mẹ ÷ vốn chủ bình quân đầu và cuối kỳ. Thiếu một thành phần thì để trống, không ước lượng. Kiểm tra chéo: lãi gộp với doanh thu
        − giá vốn, tổng 4 quý với cả năm, LNST với nguồn Vnstock; dòng tiền quý những năm cũ thường lệch số cả năm đã kiểm toán.
      </p>}
    </div>
  );
  }
}
