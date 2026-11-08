"use client";
import { useEffect, useRef, useState } from "react";
import { cell, periodLabel } from "./financial-tables";

type Kind = "money" | "pct" | "x";
type Row = { key: string | null; label: string; kind: "group" | Kind; indent: number; values: (string | null)[] };

/** Click a row: add it, click again: remove it; at most two rows, a new one replaces the one picked earliest. */
export function toggleRow(selected: string[], key: string, max = 2): string[] {
  if (selected.includes(key)) return selected.filter((k) => k !== key);
  return [...selected, key].slice(-max);
}

/** "% so cùng kỳ" alone says nothing in a legend: name it after the line above it that it measures. */
export function seriesName(rows: Row[], key: string): string {
  const i = rows.findIndex((r) => r.key === key);
  if (i < 0) return key;
  const r = rows[i];
  if (!r.label.startsWith("%")) return r.label;
  for (let k = i - 1; k >= 0; k--) if (rows[k].kind === "money" && rows[k].indent === 0) return `${rows[k].label} · ${r.label}`;
  return r.label;
}

/** Money in whole tỷ đồng as the table rounds it (so a row reading 0 draws no bar), ratios in percent, multiples as they are;
 * a missing value stays missing. */
export function plotValue(v: string | null, kind: Kind): number | null {
  if (v === null) return null;
  const n = Number(v);
  return kind === "money" ? Math.round(n / 1e9) || 0 : kind === "pct" ? n * 100 : n;
}

/** One axis per unit: the first picked on the left, a second unit on the right. */
export function axes(units: Kind[]): { left: Kind | null; right: Kind | null } {
  const distinct = [...new Set(units)];
  return { left: distinct[0] ?? null, right: distinct[1] ?? null };
}

/** The range an axis covers: bars stand on zero so zero is always in; a flat line still gets a span. */
export function scaleOf(values: (number | null)[], withZero: boolean): { lo: number; hi: number } | null {
  const known = values.filter((v): v is number => v !== null);
  if (!known.length) return null;
  let lo = Math.min(...known, ...(withZero ? [0] : [])), hi = Math.max(...known, ...(withZero ? [0] : []));
  if (lo === hi) { lo -= 1; hi += 1; }
  return { lo, hi };
}

/** Round ticks covering lo..hi, about six steps of 1, 2, 2.5 or 5 × 10ⁿ; zero falls on a tick whenever the range crosses it. */
export function niceTicks(lo: number, hi: number): number[] {
  const raw = (hi - lo) / 6, mag = 10 ** Math.floor(Math.log10(raw)), norm = raw / mag;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag;
  const start = Math.floor(lo / step + 1e-9), end = Math.ceil(hi / step - 1e-9);
  return Array.from({ length: end - start + 1 }, (_, i) => Number(((start + i) * step).toPrecision(12)) || 0);
}

type Check = { period: string; check: string; label: string; a: string | null; b: string | null };
/** Which rows each cross-check bears on: the line checked and every figure the table makes from it. */
const TOUCHES: Record<string, string[]> = {
  gross_profit: ["revenue", "cogs", "gross_profit", "gross_profit_yoy", "gross_margin"],
  revenue: ["revenue", "revenue_yoy", "gross_margin", "net_margin", "ebit_margin", "ebitda_margin", "ev_revenue"],
  npat_parent: ["npat_parent", "npat_parent_yoy", "net_margin", "pe", "roe"],
  vnstock_npat: ["npat_parent", "npat_parent_yoy", "net_margin", "pe", "roe"],
  depreciation: ["depreciation", "ebitda", "ebitda_yoy", "ebitda_margin", "ev_ebitda"],
  capex: ["capex", "fcff", "fcff_yield"],
  cfo: ["cfo", "fcff", "fcff_yield"],
};

/** Periods to star on the chart, each with the cross-checks behind the star; only checks that touch a drawn row count. */
export function flaggedFor(checks: Check[], keys: string[]): Map<string, string[]> {
  const out = new Map<string, string[]>();
  for (const c of checks) if ((TOUCHES[c.check] ?? [c.check]).some((k) => keys.includes(k))) out.set(c.period, [...(out.get(c.period) ?? []), c.label]);
  return out;
}

/** A line through known values; a missing value lifts the pen so nothing is joined across it. */
export function linePath(values: (number | null)[], x: (i: number) => number, y: (v: number) => number): string {
  let d = "", pen = false;
  values.forEach((v, i) => {
    if (v === null) { pen = false; return; }
    d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

const UNIT: Record<Kind, string> = { money: "tỷ đồng", pct: "%", x: "lần" };
const tick = (v: number, kind: Kind) => `${v.toLocaleString("vi-VN", { maximumFractionDigits: kind === "money" ? 0 : 1 })}${kind === "pct" ? "%" : kind === "x" ? "x" : ""}`;

/** A small trend in the row's last cell, over the periods shown: bars around zero for money, a broken line for ratios. */
export function Spark({ row, cols }: { row: Row; cols: number[] }) {
  if (row.kind === "group") return null;
  const kind = row.kind;
  const vals = cols.map((i) => plotValue(row.values[i], kind));
  const s = scaleOf(vals, kind === "money");
  if (!s || vals.filter((v) => v !== null).length < 2) return null;
  const W = 96, H = 22, n = vals.length, step = (W - 2) / n;
  const y = (v: number) => H - 1 - ((v - s.lo) / (s.hi - s.lo)) * (H - 2);
  return (
    <svg className="sc-spark" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Xu hướng ${row.label}`}>
      {kind === "money" ? vals.map((v, i) => v === null ? null :
        <rect key={i} x={1 + i * step + step * 0.15} width={step * 0.7} y={Math.min(y(v), y(0))} height={Math.max(0.5, Math.abs(y(v) - y(0)))}
          className={v < 0 ? "sc-neg" : "sc-s0"} />)
        : <path d={linePath(vals, (i) => 1 + i * step + step / 2, y)} className="mc-line sc-thin" />}
    </svg>
  );
}

type Series = { key: string; name: string; kind: Kind; values: (number | null)[]; raw: (string | null)[] };

/** The picked rows over the periods shown, bars for money and lines for ratios, one axis per unit; the owner's forecast is hatched. */
export function StatementChart({ rows, periods, cols, keys, forecast, checks, onRemove }: {
  rows: Row[]; periods: string[]; cols: number[]; keys: string[]; forecast: { label: string; values: Record<string, string | null> } | null;
  checks: Check[]; onRemove: (key: string) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(640);
  const [at, setAt] = useState<number | null>(null);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => setW(Math.max(260, Math.round(el.clientWidth)));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const labels = [...cols.map((i) => periodLabel(periods[i])), ...(forecast ? [forecast.label] : [])];
  const fc = forecast ? labels.length - 1 : -1;
  const series: Series[] = keys.flatMap((key) => {
    const row = rows.find((r) => r.key === key);
    if (!row || row.kind === "group") return [];
    const raw = [...cols.map((i) => row.values[i]), ...(forecast ? [forecast.values[key] ?? null] : [])];
    return [{ key, name: seriesName(rows, key), kind: row.kind, raw, values: raw.map((v) => plotValue(v, row.kind as Kind)) }];
  });
  if (!series.length) return <p className="caption">Bấm tên một dòng trong bảng để vẽ biểu đồ (tối đa 2 dòng).</p>;
  const { left, right } = axes(series.map((s) => s.kind));
  const scale = (unit: Kind | null) => unit && scaleOf(series.filter((s) => s.kind === unit).flatMap((s) => s.values), unit === "money");
  const flagged = flaggedFor(checks, series.map((s) => s.key));
  const flagAt = (i: number) => (i === fc ? undefined : flagged.get(periods[cols[i]]));
  const tl = (() => { const s = scale(left); return s ? niceTicks(s.lo, s.hi) : []; })();
  const tr = (() => { const s = scale(right); return s ? niceTicks(s.lo, s.hi) : []; })();
  const sl = tl.length ? { lo: tl[0], hi: tl[tl.length - 1] } : null, sr = tr.length ? { lo: tr[0], hi: tr[tr.length - 1] } : null;
  const H = 240, PAD = { top: 14, right: right ? 56 : 14, bottom: 28, left: 60 };
  const n = labels.length, plotW = W - PAD.left - PAD.right, step = plotW / n;
  const cx = (i: number) => PAD.left + step * i + step / 2;
  const yOf = (s: { lo: number; hi: number } | null) => (v: number) => s ? PAD.top + (1 - (v - s.lo) / (s.hi - s.lo)) * (H - PAD.top - PAD.bottom) : 0;
  const yL = yOf(sl), yR = yOf(sr);
  const yFor = (kind: Kind) => (kind === left ? yL : yR);
  const bars = series.filter((s) => s.kind === "money");
  const every = Math.max(1, Math.ceil((n * 46) / plotW));
  const swatch = (i: number) => `sc-s${i}`;
  return (
    <div className="sc">
      <div className="sc-legend" aria-label="Dòng đang vẽ">
        {series.map((s, i) => <button key={s.key} type="button" className="btn sc-chip" onClick={() => onRemove(s.key)} aria-label={`Bỏ ${s.name} khỏi biểu đồ`}>
          <span className={`sc-key ${swatch(i)}${s.kind === "money" ? "" : " line"}`} aria-hidden="true" />{s.name} <span aria-hidden="true">×</span></button>)}
        <span className="caption">{[left, right].filter(Boolean).map((u, k) => `${k ? "phải" : "trái"}: ${UNIT[u as Kind]}`).join(" · ")}</span>
      </div>
      <div className="mc-plot" ref={box}>
        <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} onPointerLeave={() => setAt(null)} role="img" aria-label={`Biểu đồ ${series.map((s) => s.name).join(" và ")}`}>
          <defs><pattern id="sc-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" className="sc-hatch-bg" /><line x1="0" y1="0" x2="0" y2="6" className="sc-hatch-line" /></pattern></defs>
          {tl.map((t, k) => <g key={`l${k}`}><line x1={PAD.left} x2={W - PAD.right} y1={yL(t)} y2={yL(t)} className={t === 0 && left === "money" ? "sc-zero" : "mc-grid"} />
            <text x={PAD.left - 6} y={yL(t) + 4} className="mc-axis" textAnchor="end">{tick(t, left!)}</text></g>)}
          {tr.map((t, k) => <text key={`r${k}`} x={W - PAD.right + 6} y={yR(t) + 4} className="mc-axis">{tick(t, right!)}</text>)}
          {right === "money" && sr && sr.lo < 0 && <line x1={PAD.left} x2={W - PAD.right} y1={yR(0)} y2={yR(0)} className="sc-zero" />}
          {bars.map((s, b) => {
            const y = yFor("money"), bw = (step * 0.7) / bars.length, idx = series.indexOf(s);
            return s.values.map((v, i) => v === null ? null :
              <rect key={`${s.key}${i}`} x={cx(i) - step * 0.35 + b * bw} width={Math.max(1, bw - 1)} y={Math.min(y(v), y(0))}
                height={Math.max(1, Math.abs(y(v) - y(0)))} className={i === fc ? "sc-fc" : swatch(idx)} />);
          })}
          {series.filter((s) => s.kind !== "money").map((s) => {
            const y = yFor(s.kind), idx = series.indexOf(s);
            const real = s.values.map((v, i) => (i === fc ? null : v));
            return <g key={s.key}>
              <path d={linePath(real, cx, y)} className={`sc-line ${swatch(idx)}`} />
              {s.values.map((v, i) => v === null ? null :
                <circle key={i} cx={cx(i)} cy={y(v)} r={i === fc ? 4 : 2.5} className={i === fc ? `sc-dot-fc ${swatch(idx)}` : `sc-dot ${swatch(idx)}`} />)}
            </g>;
          })}
          {labels.map((l, i) => (i % every === 0 || i === n - 1) &&
            <text key={l} x={cx(i)} y={H - 8} className="mc-axis" textAnchor="middle">{l}{flagAt(i) ? "*" : ""}</text>)}
          {at !== null && <line x1={cx(at)} x2={cx(at)} y1={PAD.top} y2={H - PAD.bottom} className="mc-cross" />}
          {labels.map((l, i) => <rect key={`h${l}`} x={PAD.left + step * i} y={PAD.top} width={step} height={H - PAD.top - PAD.bottom} fill="transparent"
            onPointerEnter={() => setAt(i)} onClick={() => setAt(i)} />)}
        </svg>
        {at !== null && <div className="mc-tip" style={{ left: `${Math.min(80, Math.max(20, (cx(at) / W) * 100))}%` }} role="status">
          <strong>{labels[at]}{at === fc ? " (dự phóng)" : ""}</strong>
          {series.map((s) => <div key={s.key}>{s.name}: {cell(s.raw[at], s.kind, s.key)}</div>)}
          {flagAt(at)?.map((l) => <div key={l} className="caption">* {l}</div>)}</div>}
      </div>
      <p className="caption">Ô trống trong bảng là khoảng trống trên biểu đồ, không nối qua.{forecast ? ` ${forecast.label} gạch chéo là số dự phóng của bạn, không phải số công bố.` : ""}
        {labels.some((_, i) => flagAt(i)) ? " * kỳ có chỗ lệch trong Kiểm tra chéo ở dòng đang vẽ hoặc số tính ra từ nó; chạm vào kỳ để xem." : ""}</p>
      <details className="mc-table">
        <summary>Xem số liệu</summary>
        <table aria-label="Số liệu biểu đồ bảng số tài chính">
          <thead><tr><th>Kỳ</th>{series.map((s) => <th key={s.key} className="num">{s.name}</th>)}{flagged.size > 0 && <th>Kiểm tra chéo</th>}</tr></thead>
          <tbody>{labels.map((l, i) => <tr key={l}><td>{l}{i === fc ? " (dự phóng)" : ""}</td>
            {series.map((s) => <td key={s.key} className="num">{cell(s.raw[i], s.kind, s.key)}</td>)}
            {flagged.size > 0 && <td>{flagAt(i)?.join("; ") ?? ""}</td>}</tr>)}</tbody>
        </table>
      </details>
    </div>
  );
}
