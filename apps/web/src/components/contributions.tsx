"use client";
import { useEffect, useState } from "react";
import { CalendarCheck } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd, groupDigitsInput, hanoiDate, parseMoneyInput } from "../lib/format";

type Month = { month: string; net: string; status: "met" | "short" | "none" | "pending"; short_by: string | null };
type Status = { months: Month[]; streak: number; planned: string; contributed: string };
type View = { version: number; plan: { amount: string; day: number; start: string } | null; status: Status | null; suggested_amount: string | null };

const label = (key: string) => `${key.slice(5, 7)}/${key.slice(0, 4)}`;
const nextMonth = () => { const [y, m] = hanoiDate().split("-").map(Number); return m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, "0")}`; };
const STATUS: Record<Month["status"], [string, string]> = { met: ["đã góp", "good"], short: ["thiếu", "warn"], none: ["chưa góp", "bad"], pending: ["đang chờ", ""] };

/** A fixed monthly contribution read from the ledger's deposits less withdrawals: months, streak and totals; reminders go by Telegram. */
export function Contributions() {
  const [view, setView] = useState<View | null>(null);
  const [amount, setAmount] = useState("");
  const [day, setDay] = useState("");
  const [start, setStart] = useState(nextMonth());
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>("contributions").then((v) => {
      setView(v);
      const source = v.plan?.amount ?? v.suggested_amount;
      if (source) setAmount(formatVnd(source, { unit: false }));
      if (v.plan) { setDay(String(v.plan.day)); setStart(v.plan.start); }
    }, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  async function save() {
    if (!view) return;
    const a = parseMoneyInput(amount), d = Number(day);
    if (a === null || a.includes(".") || !Number.isInteger(d) || d < 1 || d > 28 || !/^\d{4}-\d{2}$/.test(start)) {
      setMessage("Nhập số tiền góp (đồng), ngày góp từ 1 đến 28 và tháng bắt đầu."); return;
    }
    try {
      setView(await api<View>("contributions", { method: "PUT", body: { amount: a, day: d, start, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const s = view?.status;
  return (
    <section className="surface" aria-label="Góp vốn đều">
      <h2>Góp vốn đều</h2>
      <p className="caption">Mỗi tháng góp một khoản cố định; ứng dụng đọc tổng “Nộp tiền” trừ “Rút tiền” trong sổ để biết tháng đó đã góp chưa, và nhắc qua
        Telegram một lần mỗi tháng từ ngày góp nếu chưa đủ. “Đầu tư là việc nhàm chán, lặp lại hằng tháng” (VWA).</p>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <label className="field">Số tiền góp mỗi tháng (đ)<input inputMode="numeric" value={amount} disabled={!view} onChange={(e) => setAmount(groupDigitsInput(e.target.value))}
          placeholder={view?.suggested_amount ? `gợi ý ${formatVnd(view.suggested_amount)} (tích lũy hằng tháng)` : undefined} /></label>
        <label className="field">Ngày góp trong tháng<input inputMode="numeric" maxLength={2} value={day} disabled={!view} onChange={(e) => setDay(e.target.value.replace(/\D/g, ""))} /></label>
        <label className="field">Bắt đầu từ tháng<input type="month" value={start} disabled={!view} onChange={(e) => setStart(e.target.value)} /></label>
        <button type="submit" className="btn primary" disabled={!view}><CalendarCheck size={16} aria-hidden="true" />Lưu kế hoạch</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {view?.plan && s && <>
        <p>Kế hoạch: <strong>{formatVnd(view.plan.amount)}/tháng</strong>, ngày {view.plan.day}, từ {label(view.plan.start)} ·
          Chuỗi góp liên tục: <strong data-testid="contrib-streak">{s.streak} tháng</strong></p>
        <p className="caption">Tổng đã góp: {formatVnd(s.contributed)} / kế hoạch {formatVnd(s.planned)}</p>
        {s.months.length === 0 ? <p className="muted">Kế hoạch bắt đầu từ {label(view.plan.start)}.</p> :
          <ol className="contrib-months" aria-label="Các tháng góp vốn">{s.months.slice(-12).map((m) => {
            const [word, tone] = STATUS[m.status];
            return <li key={m.month} data-testid={`month-${m.month}`}><span>{label(m.month)}</span>
              <span className={`pill ${tone}`}>{word}{m.short_by ? ` ${formatVnd(m.short_by)}` : ""}</span></li>;
          })}</ol>}
      </>}
    </section>
  );
}
