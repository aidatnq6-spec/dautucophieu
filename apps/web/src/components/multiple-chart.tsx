"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../lib/api";

type Point = { month: string; value: string | null; year: string };
type Series = { points: Point[]; median: string | null; sd: string | null; latest: string | null };
type History = { symbol: string; pe: Series; pb: Series; shares: number | null; from: string | null; to: string | null; reason: string | null };

const H = 220, PAD = { top: 14, right: 58, bottom: 26, left: 36 };
const num = (v: string | number) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const monthLabel = (m: string) => `${m.slice(5)}/${m.slice(0, 4)}`;

function niceTicks(max: number): number[] {
  const step = [1, 2, 2.5, 5, 10, 20, 25, 50, 100].find((s) => max / s <= 5) ?? Math.ceil(max / 5);
  return Array.from({ length: Math.floor(max / step) + 1 }, (_, i) => i * step);
}

function Chart({ title, symbol, series, unit }: { title: string; symbol: string; series: Series; unit: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const [W, setW] = useState(640);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => setW(Math.max(240, Math.round(el.clientWidth)));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const pts = series.points;
  const values = pts.map((p) => (p.value === null ? null : Number(p.value)));
  const known = values.filter((v): v is number => v !== null);
  if (known.length === 0) {
    return <figure className="mc" aria-label={`${title} ${symbol}`}><figcaption><strong>{title}</strong></figcaption>
      <p className="muted">Không vẽ được: lợi nhuận hoặc vốn chủ âm trong cả giai đoạn.</p></figure>;
  }
  const median = series.median !== null ? Number(series.median) : null, sd = series.sd !== null ? Number(series.sd) : 0;
  const top = Math.max(...known, median !== null ? median + sd : 0) * 1.08;
  const base = niceTicks(top), step = base[1] ?? 1;
  const yMax = base[base.length - 1] < top ? base[base.length - 1] + step : base[base.length - 1];
  const ticks = base[base.length - 1] < yMax ? [...base, yMax] : base;
  const x = (i: number) => PAD.left + (pts.length === 1 ? 0 : (i / (pts.length - 1)) * (W - PAD.left - PAD.right));
  const y = (v: number) => PAD.top + (1 - v / yMax) * (H - PAD.top - PAD.bottom);
  // Gaps where the multiple is undefined (loss years) instead of a line through them.
  let d = "", pen = false;
  values.forEach((v, i) => { if (v === null) { pen = false; return; } d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`; pen = true; });
  const every = W < 420 ? 2 : 1;  // keep year labels apart on a phone
  // First plotted month of each year carries the year label.
  const years = pts.map((p, i) => ({ i, m: p.month })).filter(({ m }, k) => (k === 0 || pts[k - 1].month.slice(0, 4) !== m.slice(0, 4))
    && Number(m.slice(0, 4)) % every === 0 && x(k) > PAD.left + 12);
  const lastIdx = values.map((v, i) => (v === null ? -1 : i)).filter((i) => i >= 0).pop()!;
  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const rel = (e.clientX - box.left) / box.width;
    setHover(Math.max(0, Math.min(pts.length - 1, Math.round(rel * (pts.length - 1)))));
  };
  const h = hover !== null ? pts[hover] : null;
  return (
    <figure className="mc" aria-label={`${title} ${symbol}`}>
      <figcaption><strong>{title}</strong>
        <span className="caption"> · Hiện tại {series.latest ? num(series.latest) : "—"}{unit}
          {median !== null && <> · Trung vị {num(median)}{unit} · dải ±1 độ lệch chuẩn {num(Math.max(0, median - sd))}–{num(median + sd)}{unit}</>}</span>
      </figcaption>
      <div className="mc-plot" ref={box}>
        <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} ${symbol} theo tháng`}>
          {ticks.map((t) => <g key={t}><line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="mc-grid" />
            <text x={PAD.left - 6} y={y(t) + 4} className="mc-axis" textAnchor="end">{num(t).replace(",0", "")}</text></g>)}
          {median !== null && <>
            <rect x={PAD.left} width={W - PAD.left - PAD.right} y={y(median + sd)} height={Math.max(0, y(Math.max(0, median - sd)) - y(median + sd))} className="mc-band" />
            <line x1={PAD.left} x2={W - PAD.right} y1={y(median)} y2={y(median)} className="mc-median" />
            <text x={W - PAD.right + 10} y={y(median) + 4} className="mc-axis">Trung vị</text>
          </>}
          {years.map(({ i, m }) => <text key={m} x={x(i)} y={H - 8} className="mc-axis" textAnchor="middle">{m.slice(0, 4)}</text>)}
          <path d={d} className="mc-line" />
          <circle cx={x(lastIdx)} cy={y(values[lastIdx]!)} r={4} className="mc-dot" />
          {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={H - PAD.bottom} className="mc-cross" />}
          {hover !== null && values[hover] !== null && <circle cx={x(hover)} cy={y(values[hover]!)} r={4} className="mc-dot" />}
          <rect x={PAD.left} y={PAD.top} width={W - PAD.left - PAD.right} height={H - PAD.top - PAD.bottom} fill="transparent"
            onPointerMove={onMove} onPointerLeave={() => setHover(null)} />
        </svg>
        {h && <div className="mc-tip" style={{ left: `${Math.min(80, Math.max(20, (x(hover!) / W) * 100))}%` }} role="status">
          <strong>{monthLabel(h.month)}</strong>: {h.value ? `${num(h.value)}${unit}` : "không xác định (lỗ hoặc vốn âm)"}
          <div className="caption">theo số liệu năm {h.year}</div></div>}
      </div>
      <details className="mc-table">
        <summary>Bảng số liệu</summary>
        <table><thead><tr><th>Tháng</th><th className="num">{title.split(" ")[0]}</th><th>Năm tài chính</th></tr></thead>
          <tbody>{[...pts].reverse().map((p) => <tr key={p.month}><td>{monthLabel(p.month)}</td>
            <td className="num">{p.value ? num(p.value) : "—"}</td><td>{p.year}</td></tr>)}</tbody></table>
      </details>
    </figure>
  );
}

export function MultipleCharts({ symbol }: { symbol: string }) {
  const [data, setData] = useState<History | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<History>(`fairvalue/history/${encodeURIComponent(symbol)}`).then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted">Đang tải biểu đồ…</p>;
  if (data.reason) return <p className="muted">Chưa vẽ được biểu đồ P/E, P/B: {data.reason}.</p>;
  return (
    <section aria-label={`Biểu đồ P/E và P/B ${symbol}`}>
      <p className="caption">Mỗi tháng một điểm, {monthLabel(data.from!)}–{monthLabel(data.to!)}: giá cuối tháng (đã điều chỉnh) × số cổ phiếu hiện tại,
        chia lợi nhuận hoặc vốn chủ của năm tài chính đã công bố gần nhất (số liệu năm N dùng từ 1/4 năm N+1).</p>
      <div className="mc-grid2">
        <Chart title="P/E lịch sử" symbol={symbol} series={data.pe} unit="x" />
        <Chart title="P/B lịch sử" symbol={symbol} series={data.pb} unit="x" />
      </div>
    </section>
  );
}
