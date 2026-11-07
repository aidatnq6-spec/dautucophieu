"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../lib/api";
import { PercentileBands } from "./percentile-bands";
import { PriceMilestones } from "./price-milestones";

type Point = { month: string; value: string | null; year: string | null; basis?: string; calc?: boolean };  // year: the period behind a ticker's point; null for an index
type Series = { points: Point[]; median: string | null; sd: string | null; latest: string | null };
type Calc = { from: string; to: string; check: { tickers?: number; pe?: { months: number; mean_abs: string | null }; pb?: { months: number; mean_abs: string | null } } | null };
type History = { symbol: string; kind?: "index"; calc?: Calc | null; source?: "vndirect" | "vnstock"; pe: Series; pb: Series; shares: number | null; from: string | null; to: string | null; reason: string | null };

const H = 220, PAD = { top: 14, right: 58, bottom: 26, left: 36 };
const num = (v: string | number) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const monthLabel = (m: string) => `${m.slice(5)}/${m.slice(0, 4)}`;

/** What a ticker's point rests on: the four quarters to a quarter, a quarter's equity, or a year's report. */
export function periodText(period: string, basis: string | undefined): string {
  const q = period.includes("-Q") ? `Q${period.slice(-1)}/${period.slice(0, 4)}` : null;
  if (q && basis === "4 quý") return `4 quý đến ${q}`;
  if (q) return `vốn chủ cuối ${q}`;
  return `số liệu năm ${period}`;
}

const LABEL_GAP = 24;  // px between two year labels before the earlier one is dropped

/** Year labels at each year's first plotted month (every other year on a phone). A label with the next one closer than LABEL_GAP is
 * dropped (a lone December at the start, as the index charts from 12/2017), and one at the left edge is anchored at its start. */
export function yearLabels(months: string[], x: (i: number) => number, left: number, every: number) {
  const firsts = months.map((m, i) => ({ i, year: m.slice(0, 4) }))
    .filter(({ i, year }) => (i === 0 || months[i - 1].slice(0, 4) !== year) && Number(year) % every === 0);
  return firsts.filter((f, k) => k === firsts.length - 1 || x(firsts[k + 1].i) - x(f.i) >= LABEL_GAP)
    .map((f) => ({ ...f, anchor: (x(f.i) < left + 12 ? "start" : "middle") as "start" | "middle" }));
}

const pct1 = (v: string | null | undefined) => (v == null ? "—" : `${(Number(v) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`);

/** What the dashed, worked-out part of an index chart is, its limits, and how far the same method lands from VNDirect where both exist. */
export function calcNote(c: Calc): string {
  const ch = c.check;
  const span = `Nét đứt ${monthLabel(c.from)}–${monthLabel(c.to)}: tự tính từ ${ch?.tickers ?? "các"} mã còn niêm yết trên HOSE hôm nay (thiếu các mã đã hủy niêm yết nên quá khứ bị lệch).`;
  return ch?.pe ? `${span} Cùng cách tính so với VNDirect ở ${ch.pe.months} tháng trùng nhau: P/E lệch trung bình ${pct1(ch.pe.mean_abs)}, P/B ${pct1(ch.pb?.mean_abs)}.` : span;
}

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
  // The worked-out part of an index chart (before VNDirect's series) is drawn apart, dashed, joined to the first VNDirect point.
  let d = "", dCalc = "", pen = false, penCalc = false;
  values.forEach((v, i) => {
    if (v === null) { pen = penCalc = false; return; }
    const at = `${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    if (pts[i].calc) { dCalc += `${penCalc ? "L" : "M"}${at}`; penCalc = true; return; }
    if (penCalc) { dCalc += `L${at}`; penCalc = false; }
    d += `${pen ? "L" : "M"}${at}`; pen = true;
  });
  const every = W < 420 ? 2 : 1;  // keep year labels apart on a phone
  const years = yearLabels(pts.map((p) => p.month), x, PAD.left, every);
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
          {median !== null && <> · Trung vị {num(median)}{unit} · dải ±1 độ lệch chuẩn {num(Math.max(0, median - sd))}–{num(median + sd)}{unit}
            {[2, 3].map((k) => ` · ±${k}: ${median - k * sd > 0 ? num(median - k * sd) : "—"}–${num(median + k * sd)}${unit}`).join("")}</>}</span>
      </figcaption>
      <div className="mc-plot" ref={box}>
        <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} ${symbol} theo tháng`}>
          {ticks.map((t) => <g key={t}><line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="mc-grid" />
            <text x={PAD.left - 6} y={y(t) + 4} className="mc-axis" textAnchor="end">{num(t).replace(",0", "")}</text></g>)}
          {median !== null && <>
            <rect x={PAD.left} width={W - PAD.left - PAD.right} y={y(median + sd)} height={Math.max(0, y(Math.max(0, median - sd)) - y(median + sd))} className="mc-band" />
            <line x1={PAD.left} x2={W - PAD.right} y1={y(median)} y2={y(median)} className="mc-median" />
            {/* ±2 and ±3 standard deviations: faint dashed lines, drawn only where they fall inside the plotted range */}
            {[2, 3].flatMap((k) => [median + k * sd, median - k * sd]).filter((v) => v > 0 && v <= yMax).map((v) =>
              <line key={v} x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} className="mc-sd" data-testid="mc-sd" />)}
            <text x={W - PAD.right + 10} y={y(median) + 4} className="mc-axis">Trung vị</text>
          </>}
          {years.map(({ i, year, anchor }) => <text key={year} x={x(i)} y={H - 8} className="mc-axis" textAnchor={anchor}>{year}</text>)}
          <path d={d} className="mc-line" />
          {dCalc && <path d={dCalc} className="mc-line-calc" data-testid="mc-calc" />}
          <circle cx={x(lastIdx)} cy={y(values[lastIdx]!)} r={4} className="mc-dot" />
          {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={H - PAD.bottom} className="mc-cross" />}
          {hover !== null && values[hover] !== null && <circle cx={x(hover)} cy={y(values[hover]!)} r={4} className="mc-dot" />}
          <rect x={PAD.left} y={PAD.top} width={W - PAD.left - PAD.right} height={H - PAD.top - PAD.bottom} fill="transparent"
            onPointerMove={onMove} onPointerLeave={() => setHover(null)} />
        </svg>
        {h && <div className="mc-tip" style={{ left: `${Math.min(80, Math.max(20, (x(hover!) / W) * 100))}%` }} role="status">
          <strong>{monthLabel(h.month)}</strong>: {h.value ? `${num(h.value)}${unit}` : "không xác định (lỗ hoặc vốn âm)"}
          {h.year && <div className="caption">theo {periodText(h.year, h.basis)}</div>}
          {h.calc && <div className="caption">tự tính từ các mã còn niêm yết</div>}</div>}
      </div>
      <details className="mc-table">
        <summary>Bảng số liệu</summary>
        <table><thead><tr><th>Tháng</th><th className="num">{title.split(" ")[0]}</th>{pts[0]?.year !== null && <th>Theo số liệu</th>}</tr></thead>
          <tbody>{[...pts].reverse().map((p) => <tr key={p.month}><td>{monthLabel(p.month)}</td>
            <td className="num">{p.value ? num(p.value) : "—"}</td>{p.year !== null && <td>{periodText(p.year, p.basis)}</td>}</tr>)}</tbody></table>
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
  if (!data) return <p className="muted fx-loading" role="status">Đang tải biểu đồ…</p>;
  if (data.reason) return <p className="muted">Chưa vẽ được biểu đồ P/E, P/B: {data.reason}.</p>;
  return (
    <section aria-label={`Biểu đồ P/E và P/B ${symbol}`}>
      {data.kind === "index"
        ? <p className="caption">Mỗi tháng một điểm, {monthLabel(data.from!)}–{monthLabel(data.to!)}: P/E, P/B của chỉ số ngày cuối tháng (VNDirect).
          Trung vị và dải ±1 độ lệch chuẩn tính trên toàn bộ số liệu theo ngày (VNDirect chỉ có từ 12/2017); mức hợp lý ở bảng phía trên dùng trung vị 5 năm.
          {data.calc && <> {calcNote(data.calc)}</>}</p>
        : <p className="caption">Mỗi tháng một điểm, {monthLabel(data.from!)}–{monthLabel(data.to!)}: giá cuối tháng (đã điều chỉnh) × số cổ phiếu hiện tại,
          chia lợi nhuận 4 quý gần nhất (thiếu quý thì báo cáo năm) hoặc vốn chủ cuối kỳ đã công bố, như chuỗi theo tuần.{" "}
          {data.source === "vndirect" ? "Số của công ty mẹ theo báo cáo VNDirect; kỳ tính là đã công bố từ ngày VNDirect đưa số lên (trong 120 ngày sau khi hết kỳ), nếu không thì 45 ngày sau khi hết quý, năm từ 1/4 năm sau."
            : "Số liệu Vnstock; quý tính là đã công bố 45 ngày sau khi hết quý, năm từ 1/4 năm sau."}</p>}
      <div className="mc-grid2">
        <Chart title="P/E lịch sử" symbol={symbol} series={data.pe} unit="x" />
        <Chart title="P/B lịch sử" symbol={symbol} series={data.pb} unit="x" />
      </div>
      {data.kind !== "index" && <><PercentileBands symbol={symbol} /><PriceMilestones symbol={symbol} /></>}
    </section>
  );
}
