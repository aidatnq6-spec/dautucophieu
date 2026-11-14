"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

type Point = { symbol: string; pb: string; cheaper_months: string; months: number; growth: string; quarter: string; held: string | null;
  zone: "cheap_growing" | "cheap_shrinking" | "dear_growing" | "dear_shrinking" };
type View = { points: Point[]; missing: Record<string, string>; sectors: Record<string, string | null> };

export const ZONES: Record<Point["zone"], string> = {
  cheap_growing: "Rẻ so với chính nó, lợi nhuận đang tăng", dear_growing: "Đắt so với chính nó, lợi nhuận đang tăng",
  cheap_shrinking: "Rẻ so với chính nó, lợi nhuận đang giảm", dear_shrinking: "Đắt so với chính nó, lợi nhuận đang giảm" };
const GROWTH_EDGE = 1;  // ±100% a year: beyond it a bubble sits on the edge, its figure in the list

/** Where a bubble goes in a w × h plot: across by cheaper_months (0 left), up by growth (clipped to ±100%); r by the value held. */
export function place(p: Point, w: number, h: number, maxHeld: number): { x: number; y: number; r: number; clipped: boolean } {
  const g = Number(p.growth), clipped = Math.abs(g) > GROWTH_EDGE;
  const gy = Math.max(-GROWTH_EDGE, Math.min(GROWTH_EDGE, g));
  const r = p.held && maxHeld > 0 ? 7 + 20 * Math.sqrt(Number(p.held) / maxHeld) : 5;
  return { x: Number(p.cheaper_months) * w, y: h / 2 - (gy / GROWTH_EDGE) * (h / 2), r, clipped };
}

export function WatchQuadrant() {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<View>("watchlist/quadrant").then(setView, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const W = 900, H = 420, pad = 36;
  const maxHeld = Math.max(0, ...(view?.points ?? []).map((p) => Number(p.held ?? 0)));
  const missing = Object.entries(view?.missing ?? {});
  return (
    <section className="surface" aria-label="Bong bóng góc phần tư">
      <h2>Định giá so với chính nó và tăng trưởng lợi nhuận</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!view && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {view && <>
        {view.points.length > 0 && <svg className="wq-plot" viewBox={`0 0 ${W + pad * 2} ${H + pad * 2}`} role="img"
          aria-label={`Bong bóng góc phần tư của ${view.points.length} mã`}>
          <g transform={`translate(${pad},${pad})`}>
            <rect x={0} y={0} width={W / 2} height={H / 2} className="wq-zone wq-good" />
            <rect x={0} y={0} width={W} height={H} className="wq-frame" />
            <line x1={W / 2} x2={W / 2} y1={0} y2={H} className="wq-axis" /><line x1={0} x2={W} y1={H / 2} y2={H / 2} className="wq-axis" />
            <text x={6} y={16} className="wq-label">{ZONES.cheap_growing}</text>
            <text x={W - 6} y={16} textAnchor="end" className="wq-label">{ZONES.dear_growing}</text>
            <text x={6} y={H - 8} className="wq-label">{ZONES.cheap_shrinking}</text>
            <text x={W - 6} y={H - 8} textAnchor="end" className="wq-label">{ZONES.dear_shrinking}</text>
            <text x={0} y={H + 22} className="wq-tick">P/B rẻ nhất lịch sử</text>
            <text x={W} y={H + 22} textAnchor="end" className="wq-tick">đắt nhất lịch sử</text>
            <text x={-8} y={4} textAnchor="end" className="wq-tick">+100%</text><text x={-8} y={H} textAnchor="end" className="wq-tick">−100%</text>
            {view.points.map((p) => { const b = place(p, W, H, maxHeld);
              return <g key={p.symbol}>
                <circle cx={b.x} cy={b.y} r={b.r} className={p.held ? "wq-held" : "wq-watch"}>
                  <title>{`${p.symbol}: P/B ${formatDecimal(p.pb, 2)}, rẻ hơn ${formatRatio(p.cheaper_months, 0)} số tháng từng có; lợi nhuận 4 quý đến ${p.quarter} ${Number(p.growth) > 0 ? "+" : ""}${formatRatio(p.growth, 0)} so với 4 quý trước${p.held ? `; đang nắm ${formatVnd(p.held)}` : ""}`}</title></circle>
                <text x={b.x} y={b.y - b.r - 3} textAnchor="middle" className="wq-name">{p.symbol}{b.clipped ? "*" : ""}</text></g>; })}
          </g>
        </svg>}
        <table className="fv-table" aria-label="Vị trí từng mã">
          <thead><tr><th>Mã</th><th>Vùng</th><th className="num">P/B hiện tại</th><th className="num">Số tháng P/B thấp hơn</th>
            <th className="num">Lợi nhuận 4 quý so với 4 quý trước</th><th className="num">Đang nắm</th></tr></thead>
          <tbody>{view.points.map((p) => <tr key={p.symbol}>
            <td data-label="Mã"><Link href={`/research/${p.symbol}`}>{p.symbol}</Link></td><td data-label="Vùng">{ZONES[p.zone]}</td>
            <td className="num" data-label="P/B hiện tại">{formatDecimal(p.pb, 2)}</td>
            <td className="num" data-label="Số tháng P/B thấp hơn">{formatRatio(p.cheaper_months, 0)} của {p.months} tháng</td>
            <td className="num" data-label="Lợi nhuận 4 quý">{Number(p.growth) > 0 ? "+" : ""}{formatRatio(p.growth, 1)} (đến {p.quarter})</td>
            <td className="num" data-label="Đang nắm">{p.held ? formatVnd(p.held) : "—"}</td></tr>)}</tbody>
        </table>
        {missing.length > 0 && <p className="caption" data-testid="quadrant-missing">Chưa vẽ: {missing.map(([s, why]) => `${s} (${why})`).join("; ")}.</p>}
        <p className="caption">Ngang: P/B hôm nay so với P/B từng tháng của chính mã (từ {24} tháng trở lên): bên trái là rẻ hơn phần lớn quá khứ. Dọc: lợi nhuận sau thuế
          cổ đông công ty mẹ 4 quý gần nhất so với 4 quý trước đó (dấu * là vượt ±100%, xem số ở bảng). Bong bóng to là mã đang nắm nhiều. Bốn vùng chỉ mô tả vị trí,
          không khuyên mua hay bán: rẻ có thể vì có lý do, cần đọc cùng luận điểm và báo cáo.</p>
      </>}
    </section>
  );
}
