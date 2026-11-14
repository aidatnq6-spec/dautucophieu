"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal } from "../lib/format";

type Point = { date: string; value: string; index: string };
export type Chart = { symbol: string; points: Point[]; change: string; index_change: string; ahead: boolean };

/** Both lines of one small chart on a shared scale (min and max of the two), as SVG paths in a w × h box. */
export function linePaths(points: Point[], w: number, h: number): { stock: string; index: string; lo: number; hi: number } {
  const all = points.flatMap((p) => [Number(p.value), Number(p.index)]);
  const lo = Math.min(...all), hi = Math.max(...all);
  const x = (i: number) => (points.length > 1 ? (i * w) / (points.length - 1) : 0);
  const y = (v: number) => h - ((v - lo) * h) / (hi - lo || 1);
  const path = (key: "value" | "index") => points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(Number(p[key])).toFixed(1)}`).join(" ");
  return { stock: path("value"), index: path("index"), lo, hi };
}

const pct = (v: string) => { const n = Number(v) - 100; return `${n > 0 ? "+" : n < 0 ? "−" : ""}${formatDecimal(String(Math.abs(n)), 1)}%`; };

export function HeldCharts() {
  const [data, setData] = useState<{ charts: Chart[]; short: Record<string, string> } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<{ charts: Chart[]; short: Record<string, string> }>("held-charts").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const W = 220, H = 70;
  const short = Object.entries(data?.short ?? {});
  return (
    <section className="surface" aria-label="Lưới biểu đồ nhỏ">
      <h2>Mã đang nắm so với VN-Index, 12 tháng</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!data && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {data && (data.charts.length === 0 && short.length === 0 ? <p className="muted">Chưa nắm mã nào.</p> : <>
        <div className="sm-grid">{data.charts.map((c) => { const p = linePaths(c.points, W, H);
          return <figure key={c.symbol} className="sm-card" aria-label={`${c.symbol} ${pct(c.change)}, VN-Index ${pct(c.index_change)}`}>
            <figcaption><Link href={`/research/${c.symbol}`}><strong>{c.symbol}</strong></Link>
              <span className={c.ahead ? "fd-up" : "fd-down"}>{pct(c.change)}</span><span className="caption">VN-Index {pct(c.index_change)}</span></figcaption>
            <svg viewBox={`0 0 ${W} ${H}`} className="sm-svg" aria-hidden="true"><path d={p.index} className="sm-index" /><path d={p.stock} className={c.ahead ? "sm-up" : "sm-down"} /></svg>
          </figure>; })}</div>
        {short.length > 0 && <p className="caption">Chưa vẽ: {short.map(([s, why]) => `${s} (${why})`).join("; ")}.</p>}
        <p className="caption">Giá đóng cửa đã điều chỉnh, mỗi tuần một điểm, quy về 100 ở tuần đầu cùng VN-Index (đường xám). Xanh là mạnh hơn VN-Index, đỏ là yếu hơn.
          Xếp từ tăng nhiều nhất.</p>
      </>)}
    </section>
  );
}
