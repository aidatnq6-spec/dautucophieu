"use client";
import { useEffect, useState } from "react";
import { ChartColumn } from "lucide-react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio } from "../lib/format";
import { StatementChart, toggleRow } from "./statement-chart";

type Metric = { code: string; label: string; format: "pct0" | "pct1" | "pct2" | "times"; values: (string | null)[] };
type View = { symbol: string; kind: "bank" | "securities" | "insurance"; quarters: { date: string; label: string }[]; metrics: Metric[] };

type ChartRow = { key: string; label: string; kind: "pct" | "x"; indent: number; values: (string | null)[] };

/** The ratios as rows of the statement chart: each quarter as "2026-Q3", percentages as pct, times as multiples; gaps stay gaps. */
export function chartRows(view: View): { periods: string[]; rows: ChartRow[] } {
  const periods = view.quarters.map((q) => `${q.date.slice(0, 4)}-Q${Math.floor((Number(q.date.slice(5, 7)) - 1) / 3) + 1}`);
  const rows = view.metrics.map((m) => ({ key: m.code, label: m.label, kind: m.format === "times" ? "x" as const : "pct" as const, indent: 0, values: m.values }));
  return { periods, rows };
}

const TITLE = { bank: "ngân hàng", securities: "công ty chứng khoán", insurance: "bảo hiểm" };
function show(v: string | null, f: Metric["format"]) {
  if (v === null) return "—";
  return f === "times" ? `${formatDecimal(v, 2)} lần` : formatRatio(v, Number(f.slice(3)));
}

/** A small trend line of one metric across the quarters; gaps where a quarter has no value. */
function Spark({ values, label }: { values: (string | null)[]; label: string }) {
  const nums = values.map((v) => (v === null ? null : Number(v)));
  const known = nums.filter((v): v is number => v !== null);
  if (known.length < 2) return null;
  const W = 96, H = 24, lo = Math.min(...known), hi = Math.max(...known), span = hi - lo || 1;
  const x = (i: number) => (i / (nums.length - 1)) * (W - 4) + 2, y = (v: number) => H - 2 - ((v - lo) / span) * (H - 4);
  let d = "", pen = false;
  nums.forEach((v, i) => { if (v === null) { pen = false; return; } d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`; pen = true; });
  return <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Xu hướng ${label}`}><path d={d} className="mc-line" /></svg>;
}

/** Quarterly sector ratios of a bank, securities firm or insurer, the last eight quarters, from VNDirect's public data. */
export function SectorRatios({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [hidden, setHidden] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  useEffect(() => {
    api<View>(`fairvalue/ratios/${encodeURIComponent(symbol)}`).then((v) => {
      setPicked(v.metrics.slice(0, 2).map((m) => m.code));  // the first two ratios drawn at first, as Bảng số tài chính does
      setView(v);
    }, (e) => {
      if (e instanceof ApiError && e.failure.code === "not_a_financial") setHidden(true); else setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
    });
  }, [symbol]);
  if (hidden) return null;
  const chart = view ? chartRows(view) : null;
  return (
    <section className="surface" aria-label="Chỉ số ngành theo quý">
      <h2>Chỉ số {view ? TITLE[view.kind] : "ngành"} theo quý</h2>
      {message && <p className="errors" role="alert">{message}</p>}
      {view && chart && <>
        {chart.periods.length > 0 && <StatementChart rows={chart.rows} periods={chart.periods} cols={chart.periods.map((_, i) => i)} keys={picked}
          forecast={null} checks={[]} onRemove={(key) => setPicked((p) => p.filter((k) => k !== key))} />}
        <p className="caption">Bấm tên chỉ số để vẽ (tối đa 2 dòng).</p>
        <table className="fv-table" aria-label={`Chỉ số theo quý ${symbol}`}>
          <thead><tr><th>Chỉ số</th>{view.quarters.map((q) => <th key={q.date} className="num">{q.label}</th>)}<th>Xu hướng</th></tr></thead>
          <tbody>{view.metrics.map((m) => <tr key={m.code} className={picked.includes(m.code) ? "ft-picked" : undefined}>
            <td data-label="Chỉ số">
              {/* The label is a mouse shortcut; the icon button is the keyboard and screen-reader way to the same toggle. */}
              <strong className="ft-label" onClick={() => setPicked((p) => toggleRow(p, m.code))}>{m.label}</strong>
              <button type="button" className="ft-pick" aria-pressed={picked.includes(m.code)} aria-label={`Vẽ biểu đồ: ${m.label}`}
                title="Vẽ dòng này trên biểu đồ" onClick={() => setPicked((p) => toggleRow(p, m.code))}><ChartColumn size={13} aria-hidden="true" /></button></td>
            {m.values.map((v, i) => <td key={view.quarters[i].date} data-label={view.quarters[i].label} className="num">{show(v, m.format)}</td>)}
            <td data-label="Xu hướng"><Spark values={m.values} label={m.label} /></td>
          </tr>)}</tbody>
        </table>
        <p className="caption">Nguồn: VNDirect (dữ liệu công khai), cập nhật theo lịch chạy. NIM, ROAA, ROAE, biên lợi nhuận tính trên 4–5 quý gần nhất; các tỷ lệ
          khác tại cuối quý. Dấu — là quý nguồn chưa có số.</p>
      </>}
    </section>
  );
}
