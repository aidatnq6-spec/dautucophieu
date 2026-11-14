"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

export type Day = { date: string; status: "ok"; gain: string; return: string | null; tickers: { symbol: string; amount: string }[] }
  | { date: string; status: "missing"; missing: string[] };

/** Weeks as columns (Monday first), weekdays as rows; a weekday without a session is null. */
export function calendarWeeks(days: Day[]): (Day | null)[][] {
  if (!days.length) return [];
  const byDate = new Map(days.map((d) => [d.date, d]));
  const monday = (iso: string) => { const d = new Date(`${iso}T00:00:00Z`); d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7)); return d; };
  const first = monday(days[0].date), last = monday(days[days.length - 1].date);
  const weeks: (Day | null)[][] = [];
  for (const w = new Date(first); w <= last; w.setUTCDate(w.getUTCDate() + 7)) {
    weeks.push([0, 1, 2, 3, 4].map((i) => { const d = new Date(w); d.setUTCDate(d.getUTCDate() + i); return byDate.get(d.toISOString().slice(0, 10)) ?? null; }));
  }
  return weeks;
}

/** Cell colour by the day's return: three steps each way. */
export function dayTone(d: Day | null): string {
  if (!d) return "dc-off";
  if (d.status === "missing" || d.return === null) return "dc-none";
  const r = Number(d.return), size = Math.abs(r) >= 0.02 ? 3 : Math.abs(r) >= 0.007 ? 2 : 1;
  return r === 0 ? "dc-flat" : `dc-${r > 0 ? "g" : "r"}${size}`;
}

const dm = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const WEEKDAYS = ["T2", "T3", "T4", "T5", "T6"];

export function DailyCalendar() {
  const [days, setDays] = useState<Day[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pick, setPick] = useState<string | null>(null);
  useEffect(() => { api<{ days: Day[] }>("performance-daily").then((d) => setDays(d.days), (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const weeks = days ? calendarWeeks(days) : [];
  const chosen = days?.find((d) => d.date === pick) ?? null;
  return (
    <section className="surface" aria-label="Lịch lãi lỗ hằng ngày">
      <h2>Lịch lãi/lỗ hằng ngày</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!days && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {days && (days.length === 0 ? <p className="muted">Chưa có phiên nào từ khi sổ lệnh bắt đầu.</p> : <>
        <div className="dc-wrap"><div className="dc-grid" role="grid" aria-label="Lãi lỗ theo ngày, 26 tuần">
          <div className="dc-col dc-heads" role="row">{WEEKDAYS.map((w) => <span key={w} className="dc-head" role="rowheader">{w}</span>)}</div>
          {weeks.map((w, i) => <div key={i} className="dc-col" role="row">{w.map((d, j) => d ? <button key={d.date} type="button" role="gridcell"
            className={`dc-cell ${dayTone(d)}${pick === d.date ? " dc-on" : ""}`} aria-label={`${dm(d.date)}: ${d.status === "ok" ? `${formatVnd(d.gain)}${d.return ? ` (${formatRatio(d.return, 1)})` : ""}` : "thiếu giá"}`}
            onClick={() => setPick(d.date)} /> : <span key={j} className="dc-cell dc-off" />)}</div>)}
        </div></div>
        {chosen && <div className="notice" role="note" data-testid="day-detail"><strong>{dm(chosen.date)}:</strong>{" "}
          {chosen.status === "missing" ? `thiếu giá đóng cửa của ${chosen.missing.join(", ")}, chưa tính được.` : <>
            {Number(chosen.gain) >= 0 ? "lãi" : "lỗ"} {formatVnd(chosen.gain.replace("-", ""))}{chosen.return ? ` (${formatRatio(chosen.return, 2)})` : ""}.
            {chosen.tickers.length > 0 && <> Kéo nhiều nhất: {chosen.tickers.map((t) => `${t.symbol} ${Number(t.amount) >= 0 ? "+" : "−"}${formatVnd(t.amount.replace("-", ""))}`).join(", ")}.</>}</>}</div>}
        <p className="caption">Mỗi ô một phiên, cột là tuần. Lãi/lỗ của ngày = thay đổi giá trị tài khoản chứng khoán trừ tiền nộp/rút trong ngày, theo giá đóng cửa;
          xanh là lãi, đỏ là lỗ, đậm hơn khi biến động lớn (trên 0,7% và 2%). Ô xám là ngày thiếu giá một mã đang nắm. Bấm một ô để xem mã nào kéo nhiều nhất.</p>
      </>)}
    </section>
  );
}
