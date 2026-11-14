import { formatVnd } from "../lib/format";

export type Band = { id: string; name: string; low: string; mid: string | null; high: string; source: string; auto: boolean };
export type Bands = { rows: Band[]; close: string | null; notes: string[] };

/** The price axis of the chart: from a little below the lowest of the bars and the close to a little above the highest, on round
 * steps of 10,000 đ (5,000 under 50,000). */
export function bandAxis(rows: Band[], close: string | null): { lo: number; hi: number; ticks: number[] } {
  const values = [...rows.flatMap((r) => [Number(r.low), Number(r.high)]), ...(close ? [Number(close)] : [])];
  if (!values.length) return { lo: 0, hi: 1, ticks: [] };
  const min = Math.min(...values), max = Math.max(...values);
  const step = max < 50000 ? 5000 : max < 200000 ? 10000 : 50000;
  const lo = Math.max(0, Math.floor((min * 0.95) / step) * step), hi = Math.ceil((max * 1.05) / step) * step;
  const ticks: number[] = [];
  for (let t = lo; t <= hi; t += step) ticks.push(t);
  return { lo, hi, ticks };
}

const k = (v: number) => `${(v / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}k`;

/** Dải định giá theo từng cách: one bar per way, low to high, its middle marked, and the latest close as a red line. */
export function ValuationBands({ bands, compact = false }: { bands: Bands; compact?: boolean }) {
  if (!bands.rows.length) return <p className="muted">Chưa có cách định giá nào: nhập kịch bản, hoặc chờ đủ 24 tháng P/E, P/B.</p>;
  const W = 900, left = compact ? 130 : 170, right = 24, rowH = compact ? 38 : 42, top = 26;
  const H = top + bands.rows.length * rowH + 30;
  const { lo, hi, ticks } = bandAxis(bands.rows, bands.close);
  const x = (v: number) => left + ((v - lo) * (W - left - right)) / (hi - lo || 1);
  const close = bands.close ? Number(bands.close) : null;
  return (
    <figure className="vb-fig">
      <svg viewBox={`0 0 ${W} ${H}`} className="vb-svg" role="img" aria-label={`Dải định giá ${bands.rows.length} cách${close ? `, giá hiện tại ${formatVnd(bands.close)}` : ""}`}>
        {ticks.map((t) => <g key={t}><line x1={x(t)} x2={x(t)} y1={top - 6} y2={H - 26} className="vb-grid" />
          <text x={x(t)} y={H - 10} textAnchor="middle" className="vb-tick">{k(t)}</text></g>)}
        {bands.rows.map((r, i) => { const y = top + i * rowH + rowH / 2, l = Number(r.low), h = Number(r.high);
          return <g key={r.id}>
            <text x={left - 8} y={y + 4} textAnchor="end" className={r.auto ? "vb-name" : "vb-name vb-own"}>{r.name}</text>
            <rect x={x(l)} y={y - 7} width={Math.max(2, x(h) - x(l))} height={14} rx={3} className="vb-bar"><title>{`${r.name}: ${formatVnd(r.low)} – ${formatVnd(r.high)}${r.mid ? `, giữa ${formatVnd(r.mid)}` : ""}${r.source ? ` (${r.source})` : ""}`}</title></rect>
            {r.mid && <line x1={x(Number(r.mid))} x2={x(Number(r.mid))} y1={y - 9} y2={y + 9} className="vb-mid" />}
            <text x={x(l)} y={y + 19} textAnchor="start" className="vb-end">{k(l)}</text>
            <text x={x(h)} y={y + 19} textAnchor="end" className="vb-end">{x(h) - x(l) > 70 ? k(h) : ""}</text>
          </g>; })}
        {close !== null && <g><line x1={x(close)} x2={x(close)} y1={top - 8} y2={H - 26} className="vb-close" />
          <text x={x(close)} y={top - 12} textAnchor="middle" className="vb-close-label">Giá hiện tại {k(close)}</text></g>}
      </svg>
      <figcaption className="caption">Thanh = thấp → cao; vạch đậm = mốc giữa; vạch đỏ = giá đóng cửa gần nhất. P/E, P/B 5 năm = bội số ở phân vị 25%, trung vị, phân vị 75% của 60
        tháng (nửa giữa, bỏ các tháng bất thường) × lợi nhuận hoặc giá trị sổ sách mỗi cổ phiếu hiện tại. Tên in nghiêng là khoảng bạn tự nhập.{bands.notes.length ? ` ${bands.notes.join("; ")}.` : ""}</figcaption>
    </figure>
  );
}
