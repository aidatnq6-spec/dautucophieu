"use client";
import { useMemo, useState } from "react";
import Link from "next/link";

type Value = string | string[] | null | undefined;
export type MatrixInput = { symbol: string; sector?: string | null; values: Record<string, Value>; missing: Record<string, string> };
type Criterion = { label: string; values: Record<string, string> };
type Group = { id: string; label: string; columns: { key: string; short: string }[] };

export const GROUPS: Group[] = [
  { id: "value", label: "Định giá", columns: [{ key: "verdict", short: "So với giá hợp lý" }] },
  { id: "fundamental", label: "Cơ bản", columns: [{ key: "quality", short: "Chất lượng" }, { key: "chain", short: "Chuỗi giá trị" }] },
  { id: "flow", label: "Dòng tiền & xu hướng", columns: [{ key: "foreign20", short: "Ngoại 20 phiên" }, { key: "macd_w", short: "MACD tuần" }, { key: "macd_d", short: "MACD ngày" }, { key: "rsi_d", short: "RSI ngày" }] },
];

const SIGN: Record<string, Record<string, number>> = {
  verdict: { cheap: 1, expensive: -1 }, quality: { strong: 1, weak: -1 }, chain: { tailwind: 1, headwind: -1 }, foreign20: { buy: 1, sell: -1 }, macd_w: { up: 1, down: -1 }, macd_d: { up: 1, down: -1 },
};

/** +1 good, -1 bad, 0 neither, null no data. RSI is shown but has no direction: overbought can mean strength as well as risk. */
export function tone(key: string, value: Value): number | null {
  if (value === null || value === undefined) return null;
  const values = Array.isArray(value) ? value : [value];
  return Math.sign(values.reduce((a, v) => a + (SIGN[key]?.[v] ?? 0), 0));
}

/** The side with more signals in the group; null when none of its signals has data. */
export function groupState(group: Group, values: Record<string, Value>): number | null {
  const tones = group.columns.map((c) => tone(c.key, values[c.key])).filter((t): t is number => t !== null);
  return tones.length ? Math.sign(tones.reduce((a, b) => a + b, 0)) : null;
}

export function matrixRows<T extends MatrixInput>(rows: T[], { minGroups, sector }: { minGroups: number; sector: string }) {
  return rows.filter((r) => !sector || r.sector === sector)
    .map((r) => { const states = GROUPS.map((g) => groupState(g, r.values)); return { ...r, states, good: states.filter((s) => s === 1).length, bad: states.filter((s) => s === -1).length }; })
    .filter((r) => r.good >= minGroups)
    .sort((a, b) => b.good - a.good || a.bad - b.bad || a.symbol.localeCompare(b.symbol));
}

const show = (key: string, value: Value, criteria: Record<string, Criterion>) => (value === null || value === undefined ? "·"
  : (Array.isArray(value) ? value : [value]).map((v) => criteria[key]?.values[v] ?? v).join(", "));
const cls = (t: number | null) => (t === 1 ? "positive" : t === -1 ? "negative" : "");

/** Ma trận tín hiệu: every watched ticker against each group of signals, to see where several groups agree. It counts groups and adds up no score. */
export function SignalMatrix({ rows, criteria }: { rows: MatrixInput[]; criteria: Record<string, Criterion> }) {
  const [minGroups, setMinGroups] = useState(0);
  const [sector, setSector] = useState("");
  const sectors = useMemo(() => [...new Set(rows.map((r) => r.sector).filter((s): s is string => !!s))].sort((a, b) => a.localeCompare(b, "vi")), [rows]);
  const shown = useMemo(() => matrixRows(rows, { minGroups, sector }), [rows, minGroups, sector]);
  return (
    <section aria-label="Ma trận tín hiệu" className="sm">
      <h3>Ma trận tín hiệu</h3>
      <div className="sm-filters">
        <div role="radiogroup" aria-label="Số nhóm cùng tích cực">
          {[[0, "Mọi mã"], [2, "Từ 2 nhóm tích cực"], [3, "Cả 3 nhóm"]].map(([n, label]) => <label key={n}><input type="radio" name="sm-min" checked={minGroups === n} onChange={() => setMinGroups(n as number)} /> {label}</label>)}
        </div>
        <label className="field">Ngành<select value={sector} onChange={(e) => setSector(e.target.value)}><option value="">Tất cả ngành</option>{sectors.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
        <span className="caption" role="status">{shown.length}/{rows.length} mã</span>
      </div>
      <div className="tablewrap"><table className="sm-table" aria-label="Ma trận tín hiệu các mã theo dõi">
        <thead>
          <tr><th rowSpan={2}>Mã</th>{GROUPS.map((g) => <th key={g.id} colSpan={g.columns.length} className="sm-group">{g.label}</th>)}<th rowSpan={2} className="num">Nhóm tích cực</th><th rowSpan={2} className="num">Nhóm tiêu cực</th></tr>
          <tr>{GROUPS.flatMap((g) => g.columns.map((c) => <th key={c.key}>{c.short}</th>))}</tr>
        </thead>
        <tbody>{shown.map((r) => <tr key={r.symbol}>
          <td data-label="Mã"><Link href={`/research/${r.symbol}`}>{r.symbol}</Link>{r.sector && <span className="caption"> {r.sector}</span>}</td>
          {GROUPS.flatMap((g) => g.columns.map((c) => <td key={c.key} data-label={c.short} className={cls(tone(c.key, r.values[c.key]))} title={r.missing[c.key]}>{show(c.key, r.values[c.key], criteria)}</td>))}
          <td data-label="Nhóm tích cực" className="num positive">{r.good}</td><td data-label="Nhóm tiêu cực" className="num negative">{r.bad}</td>
        </tr>)}</tbody>
      </table></div>
      {shown.length === 0 && <p className="muted">Không có mã nào khớp.</p>}
      <p className="caption">Một nhóm tích cực khi số tín hiệu tốt nhiều hơn tín hiệu xấu trong nhóm. Dấu · là chưa có số liệu (rê chuột để xem lý do) và không tính. RSI chỉ để xem, không tính vào nhóm. Không cộng thành điểm và không gợi ý mua bán: bảng chỉ cho biết các nhóm tín hiệu có cùng chiều hay không. Chưa có cột giá mục tiêu của công ty chứng khoán vì phần mềm chưa có nguồn số này.</p>
    </section>
  );
}
