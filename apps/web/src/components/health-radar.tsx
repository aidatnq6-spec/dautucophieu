"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Wealth = { check: { rate: string; target: string } | null };
type Conc = { limit: string; tickers: { symbol: string; weight: string | null }[] };
type Passive = { result: { progress: string | null } | null };
type Contrib = { status: { planned: string; contributed: string } | null };
type Budget = { budget: { pyramid?: { layers: { id: string; status: string; target_min: string | null }[] } | null } };
type Book = { liquidity: { now: string; reserve: string } };
type Theses = { missing: string[] };
export type RadarSources = { wealth: Wealth | null; conc: Conc | null; passive: Passive | null; contrib: Contrib | null; budget: Budget | null; book: Book | null;
  theses: Theses | null };
export type Axis = { id: string; label: string; value: number | null; actual: string; need: string; why?: string };

const cap = (v: number) => Math.max(0, Math.min(1, v));

/** Seven measures, each how far the owner is towards what is needed (0–1, capped at 1); null when the inputs are not there. */
export function radarAxes(s: RadarSources): Axis[] {
  const c = s.wealth?.check, liq = s.book?.liquidity, plan = s.contrib?.status;
  const weights = (s.conc?.tickers ?? []).filter((t) => t.weight !== null).map((t) => Number(t.weight));
  const top = weights.length ? Math.max(...weights) : null;
  const ranged = (s.budget?.budget.pyramid?.layers ?? []).filter((l) => l.target_min !== null);
  const held = s.conc?.tickers.length ?? 0;
  return [
    { id: "savings", label: "Tỷ lệ tiết kiệm", value: c ? cap(Number(c.rate) / Number(c.target)) : null, actual: c ? formatRatio(c.rate, 0) : "—",
      need: c ? `≥ ${formatRatio(c.target, 0)} (bằng tuổi)` : "nhập thu chi" },
    { id: "reserve", label: "Quỹ dự phòng", value: liq && Number(liq.reserve) > 0 ? cap(Number(liq.now) / Number(liq.reserve)) : null,
      actual: liq ? formatVnd(liq.now) : "—", need: liq ? (Number(liq.reserve) > 0 ? formatVnd(liq.reserve) : "chưa đặt quỹ dự phòng") : "nhập Sổ tài sản" },
    { id: "spread", label: "Đa dạng hóa", value: top === null || !s.conc ? null : top <= Number(s.conc.limit) ? 1 : cap(Number(s.conc.limit) / top),
      actual: top === null ? "—" : `mã lớn nhất ${formatRatio(String(top), 0)}`, need: s.conc ? `≤ ${formatRatio(s.conc.limit, 0)} mỗi mã` : "—" },
    { id: "pyramid", label: "Tháp tài sản", value: ranged.length ? ranged.filter((l) => l.status === "ok").length / ranged.length : null,
      actual: ranged.length ? `${ranged.filter((l) => l.status === "ok").length}/${ranged.length} lớp trong khung` : "—", need: "mọi lớp trong khung" },
    { id: "passive", label: "Dòng tiền thụ động", value: s.passive?.result?.progress ? cap(Number(s.passive.result.progress)) : null,
      actual: s.passive?.result?.progress ? formatRatio(s.passive.result.progress, 0) : "—", need: s.passive?.result ? "100% mục tiêu" : "đặt mục tiêu" },
    { id: "contrib", label: "Góp vốn đều", value: plan && Number(plan.planned) > 0 ? cap(Number(plan.contributed) / Number(plan.planned)) : null,
      actual: plan ? formatVnd(plan.contributed) : "—", need: plan ? formatVnd(plan.planned) : "đặt kế hoạch" },
    { id: "theses", label: "Luận điểm cho mã đang nắm", value: s.theses && held > 0 ? cap((held - s.theses.missing.length) / held) : null,
      actual: s.theses && held > 0 ? `${held - s.theses.missing.length}/${held} mã` : "—", need: "mọi mã đang nắm" },
  ];
}

/** The two measures furthest from what is needed, among those with figures. */
/** A long axis name on two lines, split at the space nearest its middle. */
export function axisLines(label: string): string[] {
  if (label.length <= 14) return [label];
  const mid = label.length / 2;
  const cut = [...label].map((ch, i) => (ch === " " ? i : -1)).filter((i) => i > 0).sort((a, b) => Math.abs(a - mid) - Math.abs(b - mid))[0];
  return cut ? [label.slice(0, cut), label.slice(cut + 1)] : [label];
}

export function bottlenecks(axes: Axis[]): Axis[] {
  return axes.filter((a) => a.value !== null && a.value < 1).sort((a, b) => a.value! - b.value!).slice(0, 2);
}

async function maybe<T>(path: string): Promise<T | null> {
  try { return await api<T>(path); } catch { return null; }
}

export function HealthRadar() {
  const [s, setS] = useState<RadarSources | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all([maybe<Wealth>("wealth-check"), maybe<Conc>("concentration"), maybe<Passive>("passive-income"), maybe<Contrib>("contributions"),
      maybe<Budget>("equity-budget"), maybe<Book>("deposit-book"), maybe<Theses>("theses")])
      .then(([wealth, conc, passive, contrib, budget, book, theses]) => { if (live) setS({ wealth, conc, passive, contrib, budget, book, theses }); });
    return () => { live = false; };
  }, []);
  const axes = s ? radarAxes(s) : [];
  const R = 140, CX = 260, CY = 215, n = axes.length || 1;
  const at = (i: number, v: number) => [CX + R * v * Math.sin((2 * Math.PI * i) / n), CY - R * v * Math.cos((2 * Math.PI * i) / n)];
  const known = axes.map((a, i) => (a.value === null ? null : at(i, a.value))).filter(Boolean) as number[][];
  const narrow = bottlenecks(axes);
  return (
    <section className="surface" aria-label="Radar các yếu tố tài chính">
      <h2>Radar sức khỏe tài chính</h2>
      {!s ? <p className="muted fx-loading" role="status">Đang tải…</p> : <>
        <div className="hr-wrap">
          <svg className="hr-plot" viewBox="0 0 520 430" role="img" aria-label={`Radar ${axes.filter((a) => a.value !== null).length} trên ${axes.length} yếu tố có số`}>
            {[0.25, 0.5, 0.75, 1].map((r) => <polygon key={r} className={r === 1 ? "hr-ring hr-full" : "hr-ring"}
              points={axes.map((_, i) => at(i, r).join(",")).join(" ")} />)}
            {axes.map((a, i) => { const [x, y] = at(i, 1.14), lines = axisLines(a.label);
              const anchor = Math.abs(x - CX) < 12 ? "middle" : x > CX ? "start" : "end", top = y - (lines.length - 1) * 7 + (y > CY ? 8 : 0);
              return <g key={a.id}><line x1={CX} y1={CY} x2={at(i, 1)[0]} y2={at(i, 1)[1]} className="hr-ring" />
                <text x={x} y={top} textAnchor={anchor} className={a.value === null ? "hr-axis hr-none" : "hr-axis"}>
                  {lines.map((l, k) => <tspan key={k} x={x} dy={k ? 14 : 0}>{l}</tspan>)}
                  {a.value !== null && <tspan x={x} dy={14} className="hr-val">{Math.round(a.value * 100)}%</tspan>}</text></g>; })}
            {known.length >= 3 && <polygon className="hr-area" points={known.map((p) => p.join(",")).join(" ")} />}
            {axes.map((a, i) => a.value === null ? null : <circle key={a.id} cx={at(i, a.value)[0]} cy={at(i, a.value)[1]} r={4} className="hr-dot" />)}
          </svg>
          <table className="fv-table" aria-label="Các yếu tố sức khỏe tài chính">
            <thead><tr><th>Yếu tố</th><th className="num">Hiện trạng</th><th className="num">Mức cần</th><th className="num">Đạt</th></tr></thead>
            <tbody>{axes.map((a) => <tr key={a.id}><td data-label="Yếu tố">{a.label}</td><td className="num" data-label="Hiện trạng">{a.actual}</td>
              <td className="num" data-label="Mức cần">{a.need}</td>
              <td className="num" data-label="Đạt">{a.value === null ? "chưa có số" : formatRatio(String(a.value), 0)}</td></tr>)}</tbody>
          </table>
        </div>
        {narrow.length > 0 && <p className="notice" role="note" data-testid="radar-bottlenecks">Điểm nghẽn: {narrow.map((a) => `${a.label} (${formatRatio(String(a.value), 0)})`).join(", ")}.</p>}
        <p className="caption">Mỗi trục là mức đã đạt so với mức cần, tối đa 100% (vòng ngoài). Số lấy từ các phần Sức khỏe tài chính, Sổ tài sản, Tháp tài sản, Dòng tiền
          thụ động, Góp vốn đều, Tập trung danh mục và Luận điểm; trục chưa có số không vẽ. Không phải khuyến nghị.</p>
      </>}
    </section>
  );
}
