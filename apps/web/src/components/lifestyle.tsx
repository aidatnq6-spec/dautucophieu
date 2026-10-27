"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Month = { income: string; expenses: string };
type Lifestyle = { from: string | null; to: string | null; months: number | null; spending_change: string | null; income_change: string | null;
  cpi: string | null; verdict: "faster_than_income" | "faster_than_inflation" | "ok" | null; ready_on: string | null };
type View = { inputs: { history?: Record<string, Month> } | null; lifestyle: Lifestyle | null };

const label = (key: string) => `${key.slice(5, 7)}/${key.slice(0, 4)}`;
const signed = (r: string) => `${Number(r) > 0 ? "+" : ""}${formatRatio(r, 1)}`;
const VERDICT: Record<string, [string, string]> = {
  faster_than_income: ["Chi tiêu tăng nhanh hơn thu nhập: dấu hiệu lạm phát lối sống", "negative"],
  faster_than_inflation: ["Chi tiêu tăng nhanh hơn lạm phát nhưng chậm hơn thu nhập", ""],
  ok: ["Ổn: chi tiêu tăng chậm hơn thu nhập", "positive"],
};

/** Spending growth against income growth (and CPI), from the monthly figures kept by Sức khỏe tài chính. It names the pattern; no advice. */
export function LifestyleInflation({ refresh }: { refresh: number }) {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<View>("wealth-check").then(setView, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [refresh]);
  const l = view?.lifestyle;
  const history = Object.entries(view?.inputs?.history ?? {}).sort(([a], [b]) => b.localeCompare(a));
  return (
    <section className="surface" aria-label="Lạm phát lối sống">
      <h2>Lạm phát lối sống</h2>
      <p className="caption">Mỗi lần bấm “Kiểm tra” ở Sức khỏe tài chính, thu nhập và chi tiêu của tháng đó được lưu lại. Ứng dụng so tháng gần nhất với cùng kỳ
        12 tháng trước (hoặc tháng sớm nhất cách ít nhất 6 tháng): chi tiêu tăng nhanh hơn thu nhập là dấu hiệu lạm phát lối sống. Không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {l && (l.verdict ? <>
        <ul className="perf-bench">
          <li>Chi tiêu: <strong>{signed(l.spending_change!)}</strong> ({label(l.from!)} → {label(l.to!)})</li>
          <li>Thu nhập: <strong>{signed(l.income_change!)}</strong></li>
          <li>Lạm phát (CPI): {l.cpi ? `${signed(String(Number(l.cpi) / 100))}` : "chưa có số"}</li>
        </ul>
        <p className={VERDICT[l.verdict][1]}><strong>{VERDICT[l.verdict][0]}</strong></p>
      </> : <p className="muted">Chưa so được: cần ít nhất 6 tháng số liệu{l.ready_on ? ` (đủ vào khoảng ${label(l.ready_on)})` : ""}.</p>)}
      {view && !view.inputs && <p className="muted">Nhập thu nhập và chi tiêu ở Sức khỏe tài chính để bắt đầu.</p>}
      {history.length > 0 && <table className="fv-table cc-table" aria-label="Thu nhập và chi tiêu theo tháng">
        <thead><tr><th>Tháng</th><th className="num">Thu nhập</th><th className="num">Chi tiêu</th></tr></thead>
        <tbody>{history.map(([m, v]) => <tr key={m}><td data-label="Tháng">{label(m)}</td>
          <td data-label="Thu nhập" className="num">{formatVnd(v.income)}</td><td data-label="Chi tiêu" className="num">{formatVnd(v.expenses)}</td></tr>)}</tbody>
      </table>}
    </section>
  );
}
