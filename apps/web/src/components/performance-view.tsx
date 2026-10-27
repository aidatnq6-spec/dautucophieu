"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";

type Point = { date: string; portfolio: string; vnindex: string; value: string };
type Perf = { series: Point[]; monthly: { month: string; portfolio: string; vnindex: string }[];
  total: { portfolio: string; vnindex: string; since: string; days: number } | null; skipped_days: string[];
  benchmarks?: { days: number | null; deposit: string | null; deposit_rate: string | null; inflation: string | null; cpi_yoy: string | null;
    cpi_month: string | null; real: string | null };
  contributions: { symbol: string; cost: string; value: string | null; unrealized: string | null }[]; realized_gain: string; ledger_started_on: string | null };

const H = 220, PAD = { top: 12, right: 70, bottom: 24, left: 40 };
const pct = (v: string) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${Math.abs(Number(v) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
const tone = (v: string | null) => (v === null || Number(v) === 0 ? "" : Number(v) > 0 ? "positive" : "negative");
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const signedVnd = (v: string) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${formatVnd(v.replace(/^-/, ""))}`;

function Chart({ series }: { series: Point[] }) {
  const box = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(640);
  const [hover, setHover] = useState<number | null>(null);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => setW(Math.max(240, Math.round(el.clientWidth)));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const a = series.map((p) => Number(p.portfolio)), b = series.map((p) => Number(p.vnindex));
  const lo = Math.floor(Math.min(...a, ...b, 100) - 1), hi = Math.ceil(Math.max(...a, ...b, 100) + 1);
  const x = (i: number) => PAD.left + (series.length === 1 ? 0 : (i / (series.length - 1)) * (W - PAD.left - PAD.right));
  const y = (v: number) => PAD.top + (1 - (v - lo) / (hi - lo)) * (H - PAD.top - PAD.bottom);
  const path = (vals: number[]) => vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const ticks = [lo, Math.round((lo + hi) / 2), hi];
  const months = series.map((p, i) => ({ i, m: p.date.slice(0, 7) })).filter(({ m }, k) => k === 0 || series[k - 1].date.slice(0, 7) !== m);
  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    setHover(Math.max(0, Math.min(series.length - 1, Math.round(((e.clientX - r.left) / r.width) * (series.length - 1)))));
  };
  const h = hover !== null ? series[hover] : null;
  return (
    <div className="mc-plot" ref={box}>
      <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Danh mục và VN-Index, cùng quy về 100 ngày đầu">
        {ticks.map((t) => <g key={t}><line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="mc-grid" />
          <text x={PAD.left - 6} y={y(t) + 4} className="mc-axis" textAnchor="end">{t}</text></g>)}
        {months.map(({ i, m }) => <text key={m} x={x(i)} y={H - 6} className="mc-axis" textAnchor="middle">{`${m.slice(5)}/${m.slice(2, 4)}`}</text>)}
        <path d={path(b)} className="pf-index" />
        <path d={path(a)} className="mc-line" />
        <text x={W - PAD.right + 6} y={y(a[a.length - 1]) + 4} className="mc-axis pf-label">Danh mục</text>
        <text x={W - PAD.right + 6} y={y(b[b.length - 1]) + 4} className="mc-axis">VN-Index</text>
        {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={H - PAD.bottom} className="mc-cross" />}
        <rect x={PAD.left} y={PAD.top} width={W - PAD.left - PAD.right} height={H - PAD.top - PAD.bottom} fill="transparent"
          onPointerMove={onMove} onPointerLeave={() => setHover(null)} />
      </svg>
      {h && <div className="mc-tip" style={{ left: `${Math.min(80, Math.max(20, (x(hover!) / W) * 100))}%` }} role="status">
        <strong>{day(h.date)}</strong>: Danh mục {Number(h.portfolio).toLocaleString("vi-VN")} · VN-Index {Number(h.vnindex).toLocaleString("vi-VN")}
        <div className="caption">giá trị {formatVnd(h.value)}</div></div>}
    </div>
  );
}

const rate = (v: string) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 2 });

/** The same period at the 12-month deposit rate and at the latest CPI, and the portfolio's return after inflation. */
function Benchmarks({ b }: { b: NonNullable<Perf["benchmarks"]> }) {
  return (
    <ul className="perf-bench" aria-label="So với gửi tiết kiệm và lạm phát">
      <li>Gửi tiết kiệm 12 tháng{b.deposit_rate ? ` (${rate(b.deposit_rate)}%/năm)` : ""}: {b.deposit !== null
        ? <strong className={tone(b.deposit)}>{pct(b.deposit)}</strong> : <span className="muted">chưa có lãi suất</span>}</li>
      <li>Lạm phát{b.cpi_yoy && b.cpi_month ? ` (CPI ${rate(b.cpi_yoy)}% so cùng kỳ, tháng ${b.cpi_month.slice(5, 7)}/${b.cpi_month.slice(0, 4)})` : ""}:{" "}
        {b.inflation !== null ? <strong>{pct(b.inflation)}</strong> : <span className="muted">chưa có số CPI (tự lấy từ tin khi Tổng cục Thống kê công bố, hoặc nhập tay ở Vĩ mô)</span>}</li>
      <li>Lợi suất thực (danh mục sau khi trừ lạm phát): {b.real !== null
        ? <strong data-testid="real-return" className={tone(b.real)}>{pct(b.real)}</strong> : <span className="muted">chưa tính được</span>}</li>
    </ul>
  );
}

/** Time-weighted performance since the ledger starts (deposits and withdrawals excluded) vs VN-Index, and gains on cost by ticker. */
export function PerformanceView() {
  const [p, setP] = useState<Perf | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Perf>("performance").then(setP, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Hiệu quả danh mục">
      <h2>Hiệu quả danh mục</h2>
      {error ? <p className="errors" role="alert">{error}</p> : !p ? <p className="muted fx-loading" role="status">Đang tải…</p> : <>
        <p className="caption">Tính từ ngày đầu tiên trong sổ{p.ledger_started_on ? ` (${day(p.ledger_started_on)})` : ""}, theo thời gian và loại trừ tiền nạp/rút,
          so với VN-Index cùng các phiên. Chỉ để theo dõi, không phải khuyến nghị.</p>
        {p.total && <p>Danh mục <strong className={tone(p.total.portfolio)}>{pct(p.total.portfolio)}</strong> · VN-Index{" "}
          <strong className={tone(p.total.vnindex)}>{pct(p.total.vnindex)}</strong> <span className="caption">từ {day(p.total.since)}, {p.total.days} phiên</span></p>}
        {p.total && p.benchmarks && <Benchmarks b={p.benchmarks} />}
        {p.series.length >= 2 ? <Chart series={p.series} />
          : <p className="muted">Mới có {p.series.length} phiên có giá đủ để tính; biểu đồ sẽ dài dần theo thời gian.</p>}
        {p.monthly.length > 0 && <table className="fv-table cc-table" aria-label="Lợi nhuận theo tháng">
          <thead><tr><th>Tháng</th><th className="num">Danh mục</th><th className="num">VN-Index</th></tr></thead>
          <tbody>{[...p.monthly].reverse().map((m) => <tr key={m.month}>
            <td data-label="Tháng">{`${m.month.slice(5)}/${m.month.slice(0, 4)}`}</td>
            <td data-label="Danh mục" className={`num ${tone(m.portfolio)}`}>{pct(m.portfolio)}</td>
            <td data-label="VN-Index" className={`num ${tone(m.vnindex)}`}>{pct(m.vnindex)}</td></tr>)}</tbody>
        </table>}
        <h3>Lãi/lỗ theo giá vốn</h3>
        <p className="caption">Tính trên giá vốn trong sổ, gồm cả phần lãi/lỗ đã có trước ngày bắt đầu ghi sổ.</p>
        <table className="fv-table cc-table" aria-label="Lãi/lỗ theo giá vốn">
          <thead><tr><th>Mã</th><th className="num">Giá vốn</th><th className="num">Giá trị</th><th className="num">Lãi/lỗ chưa thực hiện</th></tr></thead>
          <tbody>{p.contributions.map((c) => <tr key={c.symbol}>
            <td data-label="Mã"><strong>{c.symbol}</strong></td>
            <td data-label="Giá vốn" className="num">{formatVnd(c.cost)}</td>
            <td data-label="Giá trị" className="num">{c.value ? formatVnd(c.value) : "Chưa có giá"}</td>
            <td data-label="Lãi/lỗ chưa thực hiện" className={`num ${tone(c.unrealized)}`}>{c.unrealized ? signedVnd(c.unrealized) : "—"}</td></tr>)}
          </tbody>
        </table>
        <p className="caption">Lãi/lỗ đã thực hiện (đã bán): <span className={tone(p.realized_gain)}>{signedVnd(p.realized_gain)}</span>.
          {p.skipped_days.length > 0 && ` Bỏ qua ${p.skipped_days.length} phiên thiếu giá.`}</p>
      </>}
    </section>
  );
}
