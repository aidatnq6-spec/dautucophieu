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
const GROWTH_EDGE = 3;  // ±300% a year on a compressed scale: beyond it a bubble sits on the edge, its figure in the list
export const GROWTH_TICKS = [-1, -0.5, 0, 0.5, 1, 3];

/** Height of a growth on the compressed scale (log(1+|g|)), −1 at −300% and below, +1 at +300% and above: most tickers sit within
 * ±100%, and a few at several hundred percent no longer squeeze them into a band. */
export function growthScale(g: number): number {
  const s = Math.log1p(Math.min(Math.abs(g), GROWTH_EDGE)) / Math.log1p(GROWTH_EDGE);
  return g < 0 ? -s : s;
}

/** Where a bubble goes in a w × h plot: across by cheaper_months (0 left), up by growth on the compressed scale; r by the value held. */
export function place(p: Point, w: number, h: number, maxHeld: number): { x: number; y: number; r: number; clipped: boolean } {
  const g = Number(p.growth);
  const r = p.held && maxHeld > 0 ? 6 + 12 * Math.sqrt(Number(p.held) / maxHeld) : 4;
  return { x: Number(p.cheaper_months) * w, y: h / 2 - growthScale(g) * (h / 2), r, clipped: Math.abs(g) > GROWTH_EDGE };
}

type Box = { x: number; y: number; w: number; h: number };
const overlaps = (a: Box, b: Box) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

/** Where each name goes: above its bubble, else below, right or left, the first spot that overlaps no name already placed and no
 * bubble; null when none is free (the name then shows on hover and in the table). Held tickers are placed first. */
export function labelSpots(items: { key: string; x: number; y: number; r: number; text: string; first: boolean }[], w: number, h: number):
  Record<string, { x: number; y: number; anchor: "middle" | "start" | "end" } | null> {
  const charW = 7, lineH = 12, placed: Box[] = [];
  const bubbles: Box[] = items.map((i) => ({ x: i.x - i.r, y: i.y - i.r, w: i.r * 2, h: i.r * 2 }));
  const out: Record<string, { x: number; y: number; anchor: "middle" | "start" | "end" } | null> = {};
  for (const i of [...items].sort((a, b) => Number(b.first) - Number(a.first))) {
    const tw = i.text.length * charW, gap = 3;
    const tries: [number, number, "middle" | "start" | "end"][] = [[i.x, i.y - i.r - gap, "middle"], [i.x, i.y + i.r + gap + lineH - 2, "middle"],
      [i.x + i.r + gap, i.y + 4, "start"], [i.x - i.r - gap, i.y + 4, "end"]];
    out[i.key] = null;
    for (const [x, y, anchor] of tries) {
      const left = anchor === "middle" ? x - tw / 2 : anchor === "start" ? x : x - tw;
      const box = { x: left, y: y - lineH + 2, w: tw, h: lineH };
      if (box.x < 0 || box.x + box.w > w || box.y < 0 || box.y + box.h > h) continue;
      if (placed.some((p) => overlaps(p, box)) || bubbles.some((b, k) => items[k].key !== i.key && overlaps(b, box))) continue;
      placed.push(box);
      out[i.key] = { x, y, anchor };
      break;
    }
  }
  return out;
}

const tip = (p: Point) => `${p.symbol}: P/B ${formatDecimal(p.pb, 2)}, rẻ hơn ${formatRatio(p.cheaper_months, 0)} số tháng từng có; lợi nhuận 4 quý đến ${p.quarter} `
  + `${Number(p.growth) > 0 ? "+" : ""}${formatRatio(p.growth, 0)} so với 4 quý trước${p.held ? `; đang nắm ${formatVnd(p.held)}` : ""}`;

export function WatchQuadrant() {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<View>("watchlist/quadrant").then(setView, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const W = 900, H = 520, pad = 44;
  const maxHeld = Math.max(0, ...(view?.points ?? []).map((p) => Number(p.held ?? 0)));
  const missing = Object.entries(view?.missing ?? {});
  return (
    <section className="surface" aria-label="Bong bóng góc phần tư">
      <h2>Định giá so với chính nó và tăng trưởng lợi nhuận</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!view && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {view && <>
        {view.points.length > 0 && (() => {
          const spots = view.points.map((p) => ({ p, b: place(p, W, H, maxHeld) }));
          const labels = labelSpots(spots.map(({ p, b }) => ({ key: p.symbol, x: b.x, y: b.y, r: b.r, text: `${p.symbol}${b.clipped ? "*" : ""}`, first: !!p.held })), W, H);
          const count = (z: Point["zone"]) => view.points.filter((p) => p.zone === z).length;
          const hidden = view.points.filter((p) => !labels[p.symbol]).length;
          return <>
            <div className="wq-zones"><span className="wq-z good">↖ {ZONES.cheap_growing} ({count("cheap_growing")})</span>
              <span className="wq-z">{ZONES.dear_growing} ({count("dear_growing")}) ↗</span></div>
            <svg className="wq-plot" viewBox={`0 0 ${W + pad * 2} ${H + pad * 2}`} role="img" aria-label={`Bong bóng góc phần tư của ${view.points.length} mã`}>
              <g transform={`translate(${pad},${pad / 2})`}>
                <rect x={0} y={0} width={W / 2} height={H / 2} className="wq-zone wq-good" />
                <rect x={0} y={0} width={W} height={H} className="wq-frame" />
                {GROWTH_TICKS.map((g) => { const y = H / 2 - growthScale(g) * (H / 2);
                  return <g key={g}><line x1={0} x2={W} y1={y} y2={y} className={g === 0 ? "wq-axis" : "wq-grid"} />
                    <text x={-6} y={y + 4} textAnchor="end" className="wq-tick">{g > 0 ? "+" : g < 0 ? "−" : ""}{Math.abs(g * 100)}%</text></g>; })}
                <line x1={W / 2} x2={W / 2} y1={0} y2={H} className="wq-axis" />
                <text x={0} y={H + 18} className="wq-tick">← P/B rẻ nhất so với lịch sử</text>
                <text x={W} y={H + 18} textAnchor="end" className="wq-tick">đắt nhất so với lịch sử →</text>
                {spots.filter(({ p }) => !p.held).map(({ p, b }) => <circle key={p.symbol} cx={b.x} cy={b.y} r={b.r} className="wq-watch"><title>{tip(p)}</title></circle>)}
                {spots.filter(({ p }) => p.held).map(({ p, b }) => <circle key={p.symbol} cx={b.x} cy={b.y} r={b.r} className="wq-held"><title>{tip(p)}</title></circle>)}
                {spots.map(({ p, b }) => { const l = labels[p.symbol];
                  return l && <text key={p.symbol} x={l.x} y={l.y} textAnchor={l.anchor} className={p.held ? "wq-name wq-name-held" : "wq-name"}>{p.symbol}{b.clipped ? "*" : ""}</text>; })}
              </g>
            </svg>
            <div className="wq-zones"><span className="wq-z">↙ {ZONES.cheap_shrinking} ({count("cheap_shrinking")})</span>
              <span className="wq-z">{ZONES.dear_shrinking} ({count("dear_shrinking")}) ↘</span></div>
            {hidden > 0 && <p className="caption">{hidden} mã nằm quá sát nhau nên ẩn tên: rê chuột lên chấm để xem, hoặc xem bảng dưới.</p>}
          </>;
        })()}
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
          cổ đông công ty mẹ 4 quý gần nhất so với 4 quý trước đó, thang nén để các mã quanh 0 không dồn cục (dấu * là vượt ±300%, xem số ở bảng). Chấm đặc, to là
          mã đang nắm (to theo giá trị); chấm rỗng là mã chỉ theo dõi. Bốn vùng chỉ mô tả vị trí,
          không khuyên mua hay bán: rẻ có thể vì có lý do, cần đọc cùng luận điểm và báo cáo.</p>
      </>}
    </section>
  );
}
