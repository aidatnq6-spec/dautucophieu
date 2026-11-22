"use client";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd, groupDigitsInput, hanoiDate, parseMoneyInput } from "../lib/format";

type Goals = { contribution?: string; savings_rate?: string; total_assets?: string };
type Row = { id: "contribution" | "savings_rate" | "total_assets"; goal: string; now: string | null; start?: string | null; share: string | null;
  pace: string | null; behind: boolean };
type View = { year: number; version: number; goals: Goals | null; progress: { pace: string; rows: Row[] } | null };

const NAME: Record<Row["id"], string> = { contribution: "Tiền góp cả năm", savings_rate: "Tỷ lệ tiết kiệm", total_assets: "Tổng tài sản cuối năm" };
const pct = (v: string) => `${Math.round(Number(v) * 100)}%`;

/** The savings rate typed as a percentage ("30" or "30,5") into a share ("0.3"); "" stays empty; anything else is null. */
export function rateInput(raw: string): string | null | "" {
  const t = raw.trim().replace(",", ".");
  if (t === "") return "";
  if (!/^\d+(\.\d+)?$/.test(t)) return null;
  const x = Number(t);
  return x > 0 && x < 100 ? String(Number((x / 100).toFixed(4))) : null;
}

/** Where one goal stands, in words: never a forecast. */
export function rowText(r: Row): string {
  if (r.id === "savings_rate") return r.now === null ? "chưa có tháng Thu chi nào đã xong" : `hiện ${pct(r.now)}, mục tiêu ${pct(r.goal)}`;
  if (r.share === null) {
    return r.id === "total_assets" && !r.start ? "chưa có ảnh chụp cuối năm trước để tính quãng đường" : "chưa có số để so";
  }
  const done = r.id === "contribution" ? `đã góp ${formatVnd(r.now ?? "0")}` : `từ ${formatVnd(r.start ?? "0")} đến ${formatVnd(r.now ?? "0")}`;
  return `${done}: ${pct(r.share)} mục tiêu, tiến độ đều ${pct(r.pace ?? "0")}`;
}

/** Mục tiêu năm (owner, 22/11/2026): up to three goals, each set against an even pace through the year. */
export function YearGoals() {
  const today = hanoiDate();
  const thisYear = Number(today.slice(0, 4));
  const [year, setYear] = useState(Number(today.slice(5, 7)) >= 11 ? thisYear + 1 : thisYear);
  const [view, setView] = useState<View | null>(null);
  const [contribution, setContribution] = useState("");
  const [rate, setRate] = useState("");
  const [total, setTotal] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>(`year-goals/${year}`).then((v) => {
      setView(v);
      setContribution(v.goals?.contribution ? formatVnd(v.goals.contribution, { unit: false }) : "");
      setRate(v.goals?.savings_rate ? String(Number(v.goals.savings_rate) * 100).replace(".", ",") : "");
      setTotal(v.goals?.total_assets ? formatVnd(v.goals.total_assets, { unit: false }) : "");
      setMessage(null);
    }, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [year]);
  async function save() {
    if (!view) return;
    const c = contribution.trim() ? parseMoneyInput(contribution) : "";
    const t = total.trim() ? parseMoneyInput(total) : "";
    const r = rateInput(rate);
    if (c === null || t === null || r === null) { setMessage("Nhập số tiền bằng đồng và tỷ lệ tiết kiệm từ trên 0 đến dưới 100%."); return; }
    try {
      setView(await api<View>(`year-goals/${year}`, { method: "PUT", body: { contribution: c || null, savings_rate: r || null, total_assets: t || null,
        expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const v = view && view.year === year ? view : null;
  return (
    <section className="surface" aria-label="Mục tiêu năm">
      <h2>Mục tiêu năm {year}</h2>
      <div className="chips" role="radiogroup" aria-label="Năm của mục tiêu">
        {[thisYear, thisYear + 1].map((y) => <button key={y} type="button" role="radio" aria-checked={year === y} className={`chip${year === y ? " on" : ""}`}
          onClick={() => setYear(y)}>{y}</button>)}
      </div>
      <p className="caption">Mục nào cũng có thể bỏ trống. Mỗi mục so với tiến độ đều theo thời gian (phần năm đã qua); đây là so sánh, không phải dự báo.
        Đầu mỗi tháng, mục chậm hơn tiến độ đều quá 10 điểm có một dòng trong Việc tài chính hôm nay.</p>
      {message && <p className="errors" role="alert">{message}</p>}
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <label className="field">Tiền góp cả năm (đồng)<input inputMode="numeric" value={contribution} onChange={(e) => setContribution(groupDigitsInput(e.target.value))} /></label>
        <label className="field">Tỷ lệ tiết kiệm (%)<input inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} /></label>
        <label className="field">Tổng tài sản cuối năm (đồng)<input inputMode="numeric" value={total} onChange={(e) => setTotal(groupDigitsInput(e.target.value))} /></label>
        <button type="submit" className="btn primary" disabled={!v}>Lưu mục tiêu</button>
      </form>
      {v?.progress && v.progress.rows.length > 0 && <ul className="ye-list" aria-label="Tiến độ mục tiêu">{v.progress.rows.map((r) => (
        <li key={r.id}><span className={`pill ${r.behind ? "warn" : "good"}`}>{r.behind ? "chậm" : "đúng nhịp"}</span>{" "}
          <strong>{NAME[r.id]}</strong> · {r.id === "savings_rate" ? pct(r.goal) : formatVnd(r.goal)}<span className="caption"> · {rowText(r)}</span></li>))}</ul>}
    </section>
  );
}
