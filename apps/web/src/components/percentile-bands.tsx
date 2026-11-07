"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../lib/api";

export type BandWindow = {
  label: string; years: number | null; weeks: number; empty_weeks: number; from: string | null; bases: Record<string, number>;
  reason: string | null; p: Record<"p10" | "p20" | "p50" | "p70" | "p80" | "p95", string | null> | null;
  min: string | null; max: string | null; mean: string | null; sd: string | null; skew: string | null; z: string | null; rank: number | null;
};
type Bands = { current: string | null; date: string | null; windows: BandWindow[]; reason: string | null };
type Weekly = { symbol: string; source?: "vndirect" | "vnstock"; reason: string | null; missing_quarters: string[]; bands: { pe: Bands; pb: Bands };
  pe: { points: { close: string }[] }; pb: { points: { close: string }[] } };
type Metric = "pb" | "pe";
export type Episode = { entry: string; multiple: string; entry_close: string; exit: string | null; exit_close: string | null; return: string | null; drawdown: string | null };
export type Episodes = { list: Episode[]; done: number; pending: number; wins: number; win_rate: string | null; median: string | null;
  worst_return: string | null; worst_drawdown: string | null; min_episodes: number };
type WhatIfSide = { multiple: string | null; price: string; close: string; date: string; change: string; basis: string; period: string; per_share: string;
  windows: { label: string; years: number | null; weeks: number; reason: string | null; rank: number | null }[]; episodes: Episodes | null; reason: string | null };
type WhatIf = { symbol: string; price: string; reason: string | null; pe: WhatIfSide | null; pb: WhatIfSide | null };
type Mode = "off" | "custom" | 5 | 10 | 15 | 20;

const NAME: Record<Metric, string> = { pb: "P/B", pe: "P/E" };
const drawn = (w: BandWindow) => w.reason === null && w.p !== null;
const fmt = (v: string | number | null) => (v === null ? "—" : Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const dayLabel = (d: string) => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;

/** From the lowest week of any drawn window to the highest P95, today's value or the assumed one; null when no window can be drawn. */
export function axisDomain(windows: BandWindow[], current: string | null, assumed: string | null = null): [number, number] | null {
  const ws = windows.filter(drawn);
  if (ws.length === 0) return null;
  const marks = [current, assumed].filter((v): v is string => v !== null).map(Number);
  return [Math.min(...ws.map((w) => Number(w.min)), ...marks), Math.max(...ws.map((w) => Number(w.p!.p95)), ...marks)];
}

/** Where the quarters come from and when a report counts as out. */
export function sourceNote(source: "vndirect" | "vnstock"): string {
  return source === "vndirect"
    ? "Lợi nhuận và vốn chủ của công ty mẹ theo báo cáo VNDirect; một kỳ tính là đã công bố từ ngày VNDirect đưa số lên nếu trong 120 ngày sau khi hết kỳ, nếu không thì 45 ngày sau khi hết quý, năm từ 1/4 năm sau."
    : "Số liệu Vnstock (8 kỳ gần nhất); quý tính là đã công bố 45 ngày sau khi hết quý, năm từ 1/4 năm sau.";
}

/** Today's close less `pct` percent, rounded to 10 đồng. */
export function presetPrice(close: string, pct: number): number {
  return Math.round((Number(close) * (100 - pct)) / 100 / 10) * 10;
}

const pct1 = (v: string) => `${Number(v) > 0 ? "+" : ""}${(Number(v) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;

/** The twelve-month result in one line: always how many episodes; a rate and a median only from the minimum sample. */
export function episodeLine(ep: Episodes): string {
  if (ep.done === 0 && ep.pending === 0) return "Chưa lần nào về mức này trong chuỗi";
  const head = ep.win_rate === null
    ? `Có lãi ${ep.wins}/${ep.done} đợt — chưa đủ mẫu để tính tỉ lệ (cần ít nhất ${ep.min_episodes} đợt)`
    : `Có lãi ${ep.wins}/${ep.done} đợt (${Math.round(Number(ep.win_rate) * 100)}%) · trung vị ${pct1(ep.median!)}`;
  return ep.pending > 0 ? `${head} · ${ep.pending} đợt chưa đủ 12 tháng` : head;
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

function Plot({ metric, symbol, bands, assumed }: { metric: Metric; symbol: string; bands: Bands; assumed: string | null }) {
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
  const domain = axisDomain(bands.windows, bands.current, assumed)!;
  const span = domain[1] - domain[0] || 1, lo = domain[0] - span * 0.03, hi = domain[1] + span * 0.03;
  const x = (v: number) => LEFT + ((v - lo) / (hi - lo)) * (W - LEFT - RIGHT);
  const H = TOP + bands.windows.length * ROW + BOTTOM;
  const ticks = Array.from({ length: 5 }, (_, i) => domain[0] + (i * (domain[1] - domain[0])) / 4);
  const at = (w: BandWindow, k: string) => Number(k === "min" ? w.min : w.p![k as keyof NonNullable<BandWindow["p"]>]);
  const cur = bands.current !== null ? Number(bands.current) : null, as = assumed !== null ? Number(assumed) : null;
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
        {as !== null && <>
          <line x1={x(as)} x2={x(as)} y1={TOP - 4} y2={H - BOTTOM} className="pb-assumed" data-testid="pb-assumed" />
          <text x={Math.min(W - RIGHT, Math.max(LEFT, x(as)))} y={H - BOTTOM + 12} className="pb-assumed-label"
            textAnchor={x(as) > W - 90 ? "end" : x(as) < LEFT + 60 ? "start" : "middle"}>giả định {fmt(as)}</text>
        </>}
      </svg>
      <p className="pb-legend" aria-hidden="true">{SEGMENTS.map((s) => <span key={s.cls}><i className={s.cls} />{s.label}</span>)}
        <span><i className="pb-now-key" />hôm nay</span>{as !== null && <span><i className="pb-assumed-key" />giả định</span>}</p>
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

const vnd = (v: string | number) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 0 });

function WhatIfPanel({ metric, result }: { metric: Metric; result: WhatIf }) {
  if (result.reason) return <p className="muted">Không tính được giá giả định: {result.reason}.</p>;
  const side = result[metric]!, other = result[metric === "pb" ? "pe" : "pb"]!;
  const ep = side.episodes;
  return (
    <div className="pb-whatif" role="region" aria-label="Kết quả giá giả định">
      <div className="pb-cards">
        <div><span className="caption">{NAME[metric]} · {NAME[metric === "pb" ? "pe" : "pb"]} tại {vnd(result.price)}</span>
          <strong>{fmt(side.multiple)} · {fmt(other.multiple)}</strong></div>
        <div><span className="caption">So giá hiện tại</span><strong>{pct1(side.change)}</strong>
          <span className="caption">giá {dayLabel(side.date)}: {vnd(side.close)}</span></div>
        <div><span className="caption">Phân vị {NAME[metric]}</span>
          <strong>{side.windows.map((w) => `${w.label} ${w.rank === null ? "—" : `P${w.rank}`}`).join(" · ") || "—"}</strong></div>
        <div><span className="caption">{metric === "pe" ? "Lợi nhuận/cổ phiếu" : "Vốn chủ/cổ phiếu"} · {side.basis} {side.period}</span><strong>{vnd(side.per_share)}</strong></div>
        <div><span className="caption">12 tháng sau các lần {NAME[metric]} về ≤ {fmt(side.multiple)}</span>
          <strong className="pb-ep">{ep ? episodeLine(ep) : side.reason}</strong></div>
        {ep && ep.done > 0 && <div><span className="caption">Tệ nhất · lỗ sâu nhất trong 12 tháng</span>
          <strong>{pct1(ep.worst_return!)} · {pct1(ep.worst_drawdown!)}</strong></div>}
      </div>
      {ep && ep.list.length > 0 && <details className="mc-table">
        <summary>Các đợt trước ({ep.list.length})</summary>
        <div className="pb-scroll"><table className="pb-table">
          <thead><tr><th>Vào vùng</th><th className="num">{NAME[metric]}</th><th className="num">Giá</th><th>12 tháng sau</th><th className="num">Giá</th>
            <th className="num">Kết quả</th><th className="num">Lỗ sâu nhất</th></tr></thead>
          <tbody>{ep.list.map((e) => <tr key={e.entry}><td>{dayLabel(e.entry)}</td><td className="num">{fmt(e.multiple)}</td><td className="num">{vnd(e.entry_close)}</td>
            <td>{e.exit ? dayLabel(e.exit) : "chưa đủ 12 tháng"}</td><td className="num">{e.exit_close ? vnd(e.exit_close) : "—"}</td>
            <td className="num">{e.return ? pct1(e.return) : "—"}</td><td className="num">{e.drawdown ? pct1(e.drawdown) : "—"}</td></tr>)}</tbody>
        </table></div>
      </details>}
      <p className="caption wrap">Bội số tại giá giả định = giá × số cổ phiếu hiện tại ÷ mẫu số của tuần mới nhất. Một đợt bắt đầu ở tuần đầu tiên {NAME[metric]} về
        mức này; đợt mới phải cách đợt trước ít nhất 1 năm để kết quả 12 tháng không chồng nhau. Giá đóng cửa tuần đã điều chỉnh, chỉ lịch sử của
        chính mã này (mã đã hủy niêm yết không có trong mẫu). Không phải dự báo.</p>
    </div>
  );
}

export function PercentileBands({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Weekly | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [metric, setMetric] = useState<Metric>("pb");
  const [mode, setMode] = useState<Mode>("off");
  const [typed, setTyped] = useState("");
  const [result, setResult] = useState<WhatIf | null>(null);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  useEffect(() => {
    api<Weekly>(`fairvalue/weekly/${encodeURIComponent(symbol)}`).then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  const pts = data?.pb.points.length ? data.pb.points : data?.pe.points ?? [];
  const close = pts.length ? pts[pts.length - 1].close : null;
  const digits = typed.replace(/\D/g, "");
  const price = mode === "off" ? null : mode === "custom" ? (digits ? Number(digits) : null) : close ? presetPrice(close, mode) : null;
  const valid = price !== null && price > 0 && price <= 10_000_000;
  useEffect(() => {
    if (!valid) return;
    const t = setTimeout(() => {
      api<WhatIf>(`fairvalue/whatif/${encodeURIComponent(symbol)}/${price}`).then((r) => { setResult(r); setWhatIfError(null); },
        (e) => setWhatIfError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
    }, 350);
    return () => clearTimeout(t);
  }, [symbol, price, valid]);
  const shown = valid && result !== null && String(price) === result.price ? result : null;
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
      <div className="pb-modes" role="group" aria-label="Giá giả định">
        <span className="caption">Giá giả định</span>
        {(["off", "custom", 5, 10, 15, 20] as const).map((m) => <button key={m} type="button" className={`btn ${mode === m ? "primary" : ""}`} aria-pressed={mode === m}
          onClick={() => setMode(m)}>{m === "off" ? "Tắt" : m === "custom" ? "Tự gõ giá" : `−${m}%`}</button>)}
      </div>
      {mode === "custom" && <label className="field pb-price"><span>Giá giả định (đồng)</span>
        <input inputMode="numeric" value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={close ? vnd(close) : ""} /></label>}
      {price !== null && !valid && <p className="errors" role="alert">Giá phải từ 1 đến 10.000.000 đồng.</p>}
      {valid && whatIfError && <p className="errors" role="alert">{whatIfError}</p>}
      {shown && <WhatIfPanel metric={metric} result={shown} />}
      <p className="caption wrap">
        Mỗi tuần một điểm, giá cuối tuần{bands.date ? ` (mới nhất ${dayLabel(bands.date)})` : ""}.
        {metric === "pe" ? " P/E theo lợi nhuận 4 quý gần nhất đã công bố; tuần thiếu quý thì theo báo cáo năm." : " P/B theo vốn chủ cuối quý đã công bố; thiếu quý thì theo cuối năm."}
        {" "}{sourceNote(data.source ?? "vnstock")} Phân vị so với chính lịch sử của mã, không phải tín hiệu mua bán.
      </p>
      {bands.reason || axisDomain(bands.windows, bands.current) === null
        ? <p className="muted">Chưa vẽ được: {bands.reason ?? bands.windows.map((w) => `${w.label}: ${w.reason}`).join(" · ")}.</p>
        : <figure className="mc" aria-label={`Dải phân vị ${NAME[metric]} ${symbol}`}>
          <Plot metric={metric} symbol={symbol} bands={bands} assumed={shown && !shown.reason ? shown[metric]!.multiple : null} />
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
