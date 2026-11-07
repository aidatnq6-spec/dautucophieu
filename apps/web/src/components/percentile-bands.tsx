"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../lib/api";

export type BandWindow = {
  label: string; years: number | null; weeks: number; empty_weeks: number; from: string | null; bases: Record<string, number>;
  reason: string | null; p: Record<"p10" | "p20" | "p50" | "p70" | "p80" | "p95", string | null> | null;
  min: string | null; max: string | null; mean: string | null; sd: string | null; skew: string | null; z: string | null; rank: number | null;
};
type Bands = { current: string | null; date: string | null; windows: BandWindow[]; reason: string | null };
type Weekly = { symbol: string; reason: string | null; missing_quarters: string[]; bands: { pe: Bands; pb: Bands } };
type Metric = "pb" | "pe";

const NAME: Record<Metric, string> = { pb: "P/B", pe: "P/E" };
const drawn = (w: BandWindow) => w.reason === null && w.p !== null;
const fmt = (v: string | number | null) => (v === null ? "—" : Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const dayLabel = (d: string) => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;

/** From the lowest week of any drawn window to the highest P95 or today's value; null when no window can be drawn. */
export function axisDomain(windows: BandWindow[], current: string | null): [number, number] | null {
  const ws = windows.filter(drawn);
  if (ws.length === 0) return null;
  const lo = Math.min(...ws.map((w) => Number(w.min)), ...(current !== null ? [Number(current)] : []));
  const hi = Math.max(...ws.map((w) => Number(w.p!.p95)), ...(current !== null ? [Number(current)] : []));
  return [lo, hi];
}

/** How many drawn windows have today's value at or below their P20, and at or below their P10. */
export function zoneCounts(windows: BandWindow[], current: string | null) {
  const ws = windows.filter(drawn), c = current === null ? null : Number(current);
  return {
    drawn: ws.length,
    p20: c === null ? 0 : ws.filter((w) => c <= Number(w.p!.p20)).length,
    p10: c === null ? 0 : ws.filter((w) => c <= Number(w.p!.p10)).length,
  };
}

const SEGMENTS: { from: "min" | "p10" | "p20" | "p50" | "p70"; to: "p10" | "p20" | "p50" | "p70" | "p95"; cls: string; label: string }[] = [
  { from: "min", to: "p10", cls: "pb-k1", label: "≤ P10" },
  { from: "p10", to: "p20", cls: "pb-k2", label: "P10–P20" },
  { from: "p20", to: "p50", cls: "pb-k3", label: "P20–P50" },
  { from: "p50", to: "p70", cls: "pb-k4", label: "P50–P70" },
  { from: "p70", to: "p95", cls: "pb-k5", label: "P70–P95" },
];
const ROW = 30, TOP = 22, BOTTOM = 26, LEFT = 64, RIGHT = 16;

function Plot({ metric, symbol, bands }: { metric: Metric; symbol: string; bands: Bands }) {
  const [W, setW] = useState(640);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => setW(Math.max(260, Math.round(el.clientWidth)));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const domain = axisDomain(bands.windows, bands.current)!;
  const span = domain[1] - domain[0] || 1, lo = domain[0] - span * 0.03, hi = domain[1] + span * 0.03;
  const x = (v: number) => LEFT + ((v - lo) / (hi - lo)) * (W - LEFT - RIGHT);
  const H = TOP + bands.windows.length * ROW + BOTTOM;
  const ticks = Array.from({ length: 5 }, (_, i) => domain[0] + (i * (domain[1] - domain[0])) / 4);
  const at = (w: BandWindow, k: string) => Number(k === "min" ? w.min : w.p![k as keyof NonNullable<BandWindow["p"]>]);
  const cur = bands.current !== null ? Number(bands.current) : null;
  return (
    <div className="mc-plot" ref={box}>
      <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label={`${NAME[metric]} ${symbol}: dải phân vị trên ${bands.windows.length} khung, hôm nay ${fmt(bands.current)}`}>
        {ticks.map((t) => <g key={t}><line x1={x(t)} x2={x(t)} y1={TOP - 6} y2={H - BOTTOM} className="mc-grid" />
          <text x={x(t)} y={H - 8} className="mc-axis" textAnchor="middle">{fmt(t)}</text></g>)}
        {bands.windows.map((w, i) => {
          const y = TOP + i * ROW;
          return <g key={w.label}>
            <text x={LEFT - 8} y={y + ROW / 2 + 4} className="mc-axis" textAnchor="end">{w.label}</text>
            {drawn(w)
              ? SEGMENTS.map((s) => <rect key={s.cls} x={x(at(w, s.from))} width={Math.max(0, x(at(w, s.to)) - x(at(w, s.from)))} y={y + 6} height={ROW - 12} className={s.cls} />)
              : <text x={LEFT + 4} y={y + ROW / 2 + 4} className="mc-axis">{w.reason}</text>}
          </g>;
        })}
        {cur !== null && <>
          <line x1={x(cur)} x2={x(cur)} y1={TOP - 4} y2={H - BOTTOM} className="pb-now" />
          <text x={Math.min(W - RIGHT, Math.max(LEFT, x(cur)))} y={TOP - 8} className="pb-now-label"
            textAnchor={x(cur) > W - 90 ? "end" : x(cur) < LEFT + 60 ? "start" : "middle"}>hôm nay {fmt(cur)}</text>
        </>}
      </svg>
      <p className="pb-legend" aria-hidden="true">{SEGMENTS.map((s) => <span key={s.cls}><i className={s.cls} />{s.label}</span>)}
        <span><i className="pb-now-key" />hôm nay</span></p>
    </div>
  );
}

function Table({ bands }: { bands: Bands }) {
  return (
    <div className="pb-scroll">
      <table className="pb-table">
        <caption className="caption">Phân vị và vị trí hôm nay</caption>
        <thead><tr><th>Khung</th><th>Từ</th><th className="num">Tuần</th><th className="num">Hôm nay</th><th className="num">z</th>
          {["P10", "P20", "P50", "P70", "P80", "P95"].map((p) => <th key={p} className="num">{p}</th>)}<th className="num">TB</th><th className="num">Skew</th></tr></thead>
        <tbody>{bands.windows.map((w) => drawn(w)
          ? <tr key={w.label}><td>{w.label}</td><td>{w.from ? `${w.from.slice(5, 7)}/${w.from.slice(0, 4)}` : "—"}</td><td className="num">{w.weeks}</td>
            <td className="num">{w.rank === null ? "—" : `P${w.rank}`}</td><td className="num">{fmt(w.z)}</td>
            {(["p10", "p20", "p50", "p70", "p80", "p95"] as const).map((k) => <td key={k} className="num">{fmt(w.p![k])}</td>)}
            <td className="num">{fmt(w.mean)}</td><td className="num">{fmt(w.skew)}</td></tr>
          : <tr key={w.label}><td>{w.label}</td><td colSpan={12} className="muted">{w.reason}</td></tr>)}</tbody>
      </table>
    </div>
  );
}

export function PercentileBands({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Weekly | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [metric, setMetric] = useState<Metric>("pb");
  useEffect(() => {
    api<Weekly>(`fairvalue/weekly/${encodeURIComponent(symbol)}`).then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted fx-loading" role="status">Đang tải dải phân vị…</p>;
  if (data.reason) return <p className="muted">Chưa có dải phân vị: {data.reason}.</p>;
  const bands = data.bands[metric], z = zoneCounts(bands.windows, bands.current);
  const all = bands.windows.reduce<Record<string, number>>((acc, w) => (w.years === null ? { ...acc, ...w.bases } : acc), {});
  const skewed = bands.windows.some((w) => drawn(w) && Number(w.skew) > 1);
  return (
    <section className="pb-section" aria-label={`Dải phân vị ${symbol}`}>
      <div className="pb-head">
        <strong>{symbol} · {NAME[metric]} hôm nay {fmt(bands.current)} — đứng ở đâu trên {bands.windows.length} khung</strong>
        <span className="pb-toggle">{(["pb", "pe"] as const).map((m) =>
          <button key={m} type="button" className={`btn ${metric === m ? "primary" : ""}`} aria-pressed={metric === m} onClick={() => setMetric(m)}>{NAME[m]}</button>)}</span>
      </div>
      <p className="caption wrap">
        Mỗi tuần một điểm, giá cuối tuần{bands.date ? ` (mới nhất ${dayLabel(bands.date)})` : ""}.
        {metric === "pe" ? " P/E theo lợi nhuận 4 quý gần nhất đã công bố; tuần thiếu quý thì theo báo cáo năm." : " P/B theo vốn chủ cuối quý đã công bố; thiếu quý thì theo cuối năm."}
        {" "}Quý tính là đã công bố 45 ngày sau khi hết quý, năm từ 1/4 năm sau. Phân vị so với chính lịch sử của mã, không phải tín hiệu mua bán.
      </p>
      {bands.reason || axisDomain(bands.windows, bands.current) === null
        ? <p className="muted">Chưa vẽ được: {bands.reason ?? bands.windows.map((w) => `${w.label}: ${w.reason}`).join(" · ")}.</p>
        : <figure className="mc" aria-label={`Dải phân vị ${NAME[metric]} ${symbol}`}>
          <Plot metric={metric} symbol={symbol} bands={bands} />
          <Table bands={bands} />
          <p className="caption wrap">
            {bands.current === null
              ? `Tuần mới nhất không có ${NAME[metric]} (${metric === "pe" ? "lỗ 4 quý" : "vốn chủ âm"}), nên không xếp được vị trí hôm nay.`
              : `${z.p20}/${z.drawn} khung đang ≤ P20 · ${z.p10}/${z.drawn} khung ≤ P10.`}
            {skewed && " Skew > 1: đuôi phải dài, trung bình bị kéo lên — đọc theo phân vị, không theo trung bình ± độ lệch chuẩn."}
            {" "}Toàn bộ: {Object.entries(all).map(([b, n]) => `${n} tuần theo ${b}`).join(", ") || "—"}.
            {data.missing_quarters.length > 0 && ` Thiếu ${data.missing_quarters.length} quý ở nguồn (${data.missing_quarters[0]} … ${data.missing_quarters[data.missing_quarters.length - 1]}), các tuần đó dùng số năm.`}
          </p>
        </figure>}
    </section>
  );
}
