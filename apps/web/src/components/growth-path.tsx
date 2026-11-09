"use client";
import { type PointerEvent, useEffect, useRef, useState } from "react";
import { formatVnd, parseMoneyInput } from "../lib/format";

export type Path = { paid: number[]; value: number[]; real: number[] | null };

/** Value at each year end: compounded monthly, the contribution added at each month's end, as the goal's own estimate does. */
export function growthPath({ capital, monthly, rate, years, inflation, raise }: { capital: number; monthly: number; rate: number; years: number; inflation?: number | null; raise?: number | null }): Path {
  const paid = [capital], value = [capital];
  let v = capital, total = capital;
  for (let y = 1; y <= years; y++) {
    const amount = monthly * (1 + (raise ?? 0) / 100) ** (y - 1);  // the contribution steps up once a year, from the second
    for (let m = 0; m < 12; m++) v = v * (1 + rate / 100 / 12) + amount;
    total += amount * 12;
    paid.push(total);
    value.push(v);
  }
  return { paid, value, real: inflation ? value.map((x, y) => x / (1 + inflation / 100) ** y) : null };
}

export const scenarioRates = (rate: number): [number, number, number] => [Math.max(rate - 2, 0), rate, rate + 2];
export const shortTy = (v: number) => (v === 0 ? "0" : `${(v / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tỷ`);
const toText = (v: number) => String(v).replace(".", ",");
const money = (v: number) => formatVnd(String(Math.round(v)));

/** Round marks from 0 to at or past the top, in at most five steps. */
export function niceTicks(max: number): number[] {
  if (max <= 0) return [0, 1];
  let power = 10 ** Math.floor(Math.log10(max) - 1);
  for (;;) {
    for (const m of [1, 2, 5]) {
      const step = m * power, count = Math.ceil(max / step);
      if (count <= 5) return Array.from({ length: count + 1 }, (_, k) => k * step);
    }
    power *= 10;
  }
}

/** A figure short enough for an axis or a line's end. */
export const compact = (v: number) => (v === 0 ? "0" : v < 1e9 ? `${Math.round(v / 1e6).toLocaleString("vi-VN")} tr` : shortTy(v));

/** Months until the capital needed is reached, by the same formula as the chart; null if not within fifty years. */
export function monthsToReach({ capital, monthly, rate, raise, required }: { capital: number; monthly: number; rate: number; raise?: number | null; required: number }): number | null {
  if (capital >= required) return 0;
  let v = capital;
  for (let m = 1; m <= 600; m++) {
    v = v * (1 + rate / 100 / 12) + monthly * (1 + (raise ?? 0) / 100) ** Math.floor((m - 1) / 12);
    if (v >= required) return m;
  }
  return null;
}

export function reachText(months: number | null): string {
  if (months === null) return "Chưa đạt vốn cần có trong 50 năm";
  if (months === 0) return "Đã đạt vốn cần có";
  const y = Math.floor(months / 12), m = months % 12;
  return `Đạt vốn cần có sau khoảng ${y ? `${y} năm${m ? ` ${m} tháng` : ""}` : `${m} tháng`}`;
}

/** Heights for the labels at the lines' ends, moved only as far as they must be not to overlap; the same order as given. */
export function spreadLabels(ys: number[], gap: number, min: number, max: number): number[] {
  const order = ys.map((_, i) => i).sort((a, b) => ys[a] - ys[b]);
  const at = order.map((i) => Math.max(ys[i], min));
  for (let k = 1; k < at.length; k++) at[k] = Math.max(at[k], at[k - 1] + gap);
  if (at.length) at[at.length - 1] = Math.min(at[at.length - 1], max);
  for (let k = at.length - 2; k >= 0; k--) at[k] = Math.min(at[k], at[k + 1] - gap);
  const out = [...ys];
  order.forEach((i, k) => { out[i] = at[k]; });
  return out;
}

/** The year nearest the pointer, inside the plot. */
export const yearAt = (px: number, left: number, right: number, years: number) => Math.min(Math.max(Math.round(((px - left) / (right - left)) * years), 0), years);

const COLORS = ["var(--focus)", "var(--brand)", "var(--good)"];
const L = 52, T = 14, B = 26;

/** How capital plus the monthly contribution would grow at three rates the owner sets. An illustration of assumptions, not a forecast. */
export function GrowthPath({ capital, monthly, rate, required }: { capital: number; monthly: number; rate: number; required: number }) {
  const [years, setYears] = useState("20");
  const [rates, setRates] = useState(() => scenarioRates(rate).map(toText));
  const [inflation, setInflation] = useState("");
  const [raise, setRaise] = useState("");
  const [W, setW] = useState(640);  // drawn at the width it is shown at, so its text stays the size of the page's
  const [hover, setHover] = useState<number | null>(null);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => setW((old) => { const next = Math.round(el.clientWidth); return next > 0 ? next : old; });
    measure();
    const seen = new ResizeObserver(measure);
    seen.observe(el);
    return () => seen.disconnect();
  }, []);
  const n = Math.min(Math.max(Math.round(Number(years) || 0), 1), 50);
  const parsed = rates.map((r) => { const p = parseMoneyInput(r); return p === null ? null : Number(p); });
  const infl = inflation.trim() ? parseMoneyInput(inflation) : null;
  const raised = raise.trim() ? parseMoneyInput(raise) : null;
  const yearly = raised === null ? null : Number(raised);
  const badRaise = raise.trim() !== "" && (raised === null || Number(raised) > 100);
  const invalid = parsed.some((r) => r === null || r < 0 || r > 100) || badRaise;
  const paths = invalid ? [] : parsed.map((r, i) => growthPath({ capital, monthly, rate: r!, years: n, inflation: i === 1 && infl ? Number(infl) : null, raise: yearly }));
  const base = paths[1];
  const narrow = W < 480, R = narrow ? 62 : 104, H = narrow ? 240 : 300;
  const ticks = niceTicks(Math.max(1, required, ...paths.flatMap((p) => p.value)));
  const top = ticks[ticks.length - 1];
  const x = (y: number) => L + ((W - L - R) * y) / n;
  const yOf = (v: number) => H - B - ((H - B - T) * Math.min(v, top)) / top;
  const line = (s: number[]) => s.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${yOf(v).toFixed(1)}`).join(" ");
  const names = ["Thấp", "Cơ sở", "Cao"];
  const ends = invalid ? [] : [...paths.map((p, i) => ({ name: names[i], v: p.value[n], color: COLORS[i] })), { name: "Đã góp", v: base.paid[n], color: "var(--muted)" },
    ...(base.real ? [{ name: "Sức mua", v: base.real[n], color: "var(--brand)" }] : [])];
  const endAt = spreadLabels(ends.map((e) => yOf(e.v) + 4), 15, T + 4, H - B);
  const point = (e: PointerEvent<SVGSVGElement>) => setHover(yearAt(e.clientX - e.currentTarget.getBoundingClientRect().left, L, W - R, n));
  const shown = hover !== null && !invalid ? Math.min(hover, n) : null;
  return (
    <section className="gp" aria-label="Đường tăng trưởng tài sản">
      <h3>Đường tăng trưởng tài sản</h3>
      <p className="caption">Vốn hiện có {money(capital)}, góp đều {money(monthly)}/tháng.</p>
      <div className="gp-inputs">
        <label className="field">Số năm<input type="number" min={1} max={50} value={years} onChange={(e) => setYears(e.target.value)} /></label>
        {names.map((name, i) => <label key={name} className="field">Lợi suất {name.toLowerCase()} (%/năm)
          <input inputMode="decimal" value={rates[i]} onChange={(e) => setRates((r) => r.map((v, k) => (k === i ? e.target.value : v)))} /></label>)}
        <label className="field">Lạm phát giả định (%/năm)<input inputMode="decimal" value={inflation} placeholder="trống = không tính" onChange={(e) => setInflation(e.target.value)} /></label>
        <label className="field">Tăng tiền góp mỗi năm (%)<input inputMode="decimal" value={raise} placeholder="trống = giữ nguyên" onChange={(e) => setRaise(e.target.value)} /></label>
      </div>
      {invalid && <p className="errors" role="alert">{badRaise ? "Mức tăng tiền góp phải là số từ 0 đến 100." : "Lợi suất phải là số từ 0 đến 100."}</p>}
      {!invalid && <div className="kpi-row gp-cards">{names.map((name, i) => <div key={name} data-testid={`gp-card-${i}`}>
        <span className="kpi-label"><span className="gp-swatch" style={{ background: COLORS[i] }} />{name} {rates[i]}% · sau {n} năm</span>
        <strong>{money(paths[i].value[n])}</strong>
        <span className="kpi-note">{reachText(monthsToReach({ capital, monthly, rate: parsed[i]!, raise: yearly, required }))}</span></div>)}</div>}
      <div className="gp-plot" ref={box}>
        {!invalid && <>
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" className="gp-chart" onPointerMove={point} onPointerDown={point} onPointerLeave={() => setHover(null)}
            aria-label={`Sau ${n} năm: ${names.map((name, i) => `${name} ${money(paths[i].value[n])}`).join(", ")}; đã góp ${money(base.paid[n])}; vốn cần có ${money(required)}`}>
            {ticks.map((v) => <g key={v}><line x1={L} x2={W - R} y1={yOf(v)} y2={yOf(v)} stroke="var(--line)" />
              <text x={L - 6} y={yOf(v) + 4} textAnchor="end" className="gp-tick">{compact(v)}</text></g>)}
            {Array.from({ length: n + 1 }, (_, y) => y).filter((y) => y % Math.max(1, Math.round(n / 5)) === 0).map((y) => <text key={y} x={x(y)} y={H - 8} textAnchor="middle" className="gp-tick">{y === 0 ? "Nay" : `${y} năm`}</text>)}
            <line x1={L} x2={W - R} y1={yOf(required)} y2={yOf(required)} stroke="var(--bad)" strokeDasharray="2 4" />
            <text x={L + 6} y={yOf(required) - 5} className="gp-end" fill="var(--bad)">Vốn cần có {compact(required)}</text>
            <path d={line(base.paid)} fill="none" stroke="var(--muted)" strokeWidth={1.5} strokeDasharray="5 4" />
            {base.real && <path d={line(base.real)} fill="none" stroke="var(--brand)" strokeWidth={1.5} strokeDasharray="1 3" />}
            {paths.map((p, i) => <path key={names[i]} d={line(p.value)} fill="none" stroke={COLORS[i]} strokeWidth={i === 1 ? 2.5 : 1.75} />)}
            {ends.map((e, i) => <text key={e.name} x={W - R + 6} y={endAt[i]} className="gp-end" fill={e.color}>{narrow ? compact(e.v) : `${e.name} ${compact(e.v)}`}</text>)}
            {shown !== null && <g><line x1={x(shown)} x2={x(shown)} y1={T} y2={H - B} stroke="var(--muted)" />
              {paths.map((p, i) => <circle key={names[i]} cx={x(shown)} cy={yOf(p.value[shown])} r={3.5} fill={COLORS[i]} />)}</g>}
          </svg>
          {shown !== null && <div className="gp-tip" data-testid="gp-tip" style={{ left: x(shown) > W / 2 ? x(shown) - 186 : x(shown) + 12 }}>
            <strong>{shown === 0 ? "Hôm nay" : `Sau ${shown} năm`}</strong>
            {[...paths.map((p, i) => [names[i], p.value[shown]] as const).reverse(), ["Đã góp", base.paid[shown]] as const].map(([name, v]) => <div key={name}><span>{name}</span><span>{money(v)}</span></div>)}
          </div>}
        </>}
      </div>
      {!invalid && <>
        {base.real && <p className="caption">Đường chấm: Cơ sở theo sức mua hôm nay {money(base.real[n])}.</p>}
        <p className="caption">Đường nét đứt là tiền đã góp. Lợi suất là <strong>giả định</strong>, giữ nguyên suốt thời gian; thực tế lên xuống hằng năm và có thể lỗ. Không phải dự báo. Mức tăng tiền góp chỉ áp dụng cho khối này.</p>
        <details className="mc-table"><summary>Xem số liệu theo năm</summary>
          <div className="tablewrap"><table aria-label="Tăng trưởng tài sản theo năm">
            <thead><tr><th>Năm</th><th className="num">Tiền đã góp</th>{names.map((name) => <th key={name} className="num">{name}</th>)}{base.real && <th className="num">Cơ sở theo sức mua hôm nay</th>}</tr></thead>
            <tbody>{base.paid.map((p, y) => <tr key={y}><td>{y}</td><td className="num">{money(p)}</td>{paths.map((path, i) => <td key={names[i]} className="num">{money(path.value[y])}</td>)}
              {base.real && <td className="num">{money(base.real[y])}</td>}</tr>)}</tbody></table></div>
        </details>
      </>}
    </section>
  );
}
