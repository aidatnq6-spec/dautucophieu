"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio } from "../lib/format";

type Metric = { code: string; label: string; format: "pct0" | "pct1" | "pct2" | "times"; values: (string | null)[] };
type View = { symbol: string; kind: "bank" | "securities" | "insurance"; quarters: { date: string; label: string }[]; metrics: Metric[] };

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
  useEffect(() => {
    api<View>(`fairvalue/ratios/${encodeURIComponent(symbol)}`).then(setView, (e) => {
      if (e instanceof ApiError && e.failure.code === "not_a_financial") setHidden(true); else setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
    });
  }, [symbol]);
  if (hidden) return null;
  return (
    <section className="surface" aria-label="Chỉ số ngành theo quý">
      <h2>Chỉ số {view ? TITLE[view.kind] : "ngành"} theo quý</h2>
      {message && <p className="errors" role="alert">{message}</p>}
      {view && <>
        <table className="fv-table" aria-label={`Chỉ số theo quý ${symbol}`}>
          <thead><tr><th>Chỉ số</th>{view.quarters.map((q) => <th key={q.date} className="num">{q.label}</th>)}<th>Xu hướng</th></tr></thead>
          <tbody>{view.metrics.map((m) => <tr key={m.code}>
            <td data-label="Chỉ số"><strong>{m.label}</strong></td>
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
