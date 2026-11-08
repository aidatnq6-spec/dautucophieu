"use client";
import { useState } from "react";
import { formatVnd, parseMoneyInput } from "../lib/format";

export type Path = { paid: number[]; value: number[]; real: number[] | null };

/** Value at each year end: compounded monthly, the contribution added at each month's end, as the goal's own estimate does. */
export function growthPath({ capital, monthly, rate, years, inflation }: { capital: number; monthly: number; rate: number; years: number; inflation?: number | null }): Path {
  const paid = [capital], value = [capital];
  let v = capital;
  for (let y = 1; y <= years; y++) {
    for (let m = 0; m < 12; m++) v = v * (1 + rate / 100 / 12) + monthly;
    paid.push(capital + monthly * 12 * y);
    value.push(v);
  }
  return { paid, value, real: inflation ? value.map((x, y) => x / (1 + inflation / 100) ** y) : null };
}

export const scenarioRates = (rate: number): [number, number, number] => [Math.max(rate - 2, 0), rate, rate + 2];
export const shortTy = (v: number) => (v === 0 ? "0" : `${(v / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tỷ`);
const toText = (v: number) => String(v).replace(".", ",");
const money = (v: number) => formatVnd(String(Math.round(v)));

const W = 640, H = 270, L = 58, R = 12, T = 12, B = 26;
const COLORS = ["var(--muted)", "var(--brand)", "var(--good)"];

/** How capital plus the monthly contribution would grow at three rates the owner sets. An illustration of assumptions, not a forecast. */
export function GrowthPath({ capital, monthly, rate, required }: { capital: number; monthly: number; rate: number; required: number }) {
  const [years, setYears] = useState("20");
  const [rates, setRates] = useState(() => scenarioRates(rate).map(toText));
  const [inflation, setInflation] = useState("");
  const n = Math.min(Math.max(Math.round(Number(years) || 0), 1), 50);
  const parsed = rates.map((r) => { const p = parseMoneyInput(r); return p === null ? null : Number(p); });
  const infl = inflation.trim() ? parseMoneyInput(inflation) : null;
  const invalid = parsed.some((r) => r === null || r < 0 || r > 100);
  const paths = invalid ? [] : parsed.map((r, i) => growthPath({ capital, monthly, rate: r!, years: n, inflation: i === 1 && infl ? Number(infl) : null }));
  const base = paths[1];
  const top = Math.max(1, required, ...paths.flatMap((p) => p.value));
  const x = (y: number) => L + ((W - L - R) * y) / n;
  const yOf = (v: number) => H - B - ((H - B - T) * Math.min(v, top)) / top;
  const line = (s: number[]) => s.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${yOf(v).toFixed(1)}`).join(" ");
  const names = ["Thấp", "Cơ sở", "Cao"];
  return (
    <section className="gp" aria-label="Đường tăng trưởng tài sản">
      <h3>Đường tăng trưởng tài sản</h3>
      <p className="caption">Vốn hiện có {money(capital)}, góp đều {money(monthly)}/tháng. Ba mức lợi suất do bạn đặt là <strong>giả định</strong>, giữ nguyên suốt thời gian: thực tế lên xuống hằng năm và có thể lỗ. Không phải dự báo.</p>
      <div className="eb-form">
        <label className="field">Số năm<input type="number" min={1} max={50} value={years} onChange={(e) => setYears(e.target.value)} /></label>
        {names.map((name, i) => <label key={name} className="field">Lợi suất {name.toLowerCase()} (%/năm)
          <input inputMode="decimal" value={rates[i]} onChange={(e) => setRates((r) => r.map((v, k) => (k === i ? e.target.value : v)))} /></label>)}
        <label className="field">Lạm phát giả định (%/năm)<input inputMode="decimal" value={inflation} placeholder="để trống = không tính" onChange={(e) => setInflation(e.target.value)} /></label>
      </div>
      {invalid ? <p className="errors" role="alert">Lợi suất phải là số từ 0 đến 100.</p> : <>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" className="gp-chart" aria-label={`Sau ${n} năm: ${names.map((name, i) => `${name} ${money(paths[i].value[n])}`).join(", ")}; đã góp ${money(base.paid[n])}`}>
          {[0, 0.25, 0.5, 0.75, 1].map((f) => <g key={f}><line x1={L} x2={W - R} y1={yOf(top * f)} y2={yOf(top * f)} stroke="var(--line)" />
            <text x={L - 6} y={yOf(top * f) + 4} textAnchor="end" className="gp-tick">{shortTy(top * f)}</text></g>)}
          {Array.from({ length: n + 1 }, (_, y) => y).filter((y) => y % Math.max(1, Math.round(n / 5)) === 0).map((y) => <text key={y} x={x(y)} y={H - 8} textAnchor="middle" className="gp-tick">{y === 0 ? "Nay" : `${y} năm`}</text>)}
          {required <= top && <line x1={L} x2={W - R} y1={yOf(required)} y2={yOf(required)} stroke="var(--bad)" strokeDasharray="2 4" />}
          <path d={line(base.paid)} fill="none" stroke="var(--ink)" strokeWidth={1.5} strokeDasharray="5 4" />
          {base.real && <path d={line(base.real)} fill="none" stroke="var(--brand)" strokeWidth={1.5} strokeDasharray="1 3" />}
          {paths.map((p, i) => <path key={names[i]} d={line(p.value)} fill="none" stroke={COLORS[i]} strokeWidth={i === 1 ? 2.5 : 1.75} />)}
        </svg>
        <ul className="gp-legend">
          {names.map((name, i) => <li key={name}><span className="gp-swatch" style={{ background: COLORS[i] }} />{name} {rates[i]}%: <strong>{money(paths[i].value[n])}</strong></li>)}
          <li><span className="gp-swatch gp-dash" />Tiền đã góp: {money(base.paid[n])}</li>
          {base.real && <li><span className="gp-swatch" style={{ background: "var(--brand)", opacity: 0.5 }} />Cơ sở theo sức mua hôm nay: {money(base.real[n])}</li>}
          <li><span className="gp-swatch" style={{ background: "var(--bad)" }} />Vốn cần có: {money(required)}</li>
        </ul>
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
