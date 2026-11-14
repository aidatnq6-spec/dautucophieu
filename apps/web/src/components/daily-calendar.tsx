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

export type Month = { month: string; weeks: (Day | "off" | null)[][]; gain: number; up: number; down: number; missing: number };

/** One calendar per month, newest first: weeks as rows (Monday first, weekdays only); a weekday without a session is null, a day of
 * another month "off". With the month's total gain and its counts of up and down sessions. */
export function monthCalendars(days: Day[]): Month[] {
  const byMonth = new Map<string, Day[]>();
  for (const d of days) byMonth.set(d.date.slice(0, 7), [...(byMonth.get(d.date.slice(0, 7)) ?? []), d]);
  const out: Month[] = [];
  for (const [month, list] of byMonth) {
    const [y, m] = month.split("-").map(Number), byDate = new Map(list.map((d) => [d.date, d]));
    const first = new Date(Date.UTC(y, m - 1, 1)), last = new Date(Date.UTC(y, m, 0));
    const start = new Date(first); start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7));
    const weeks: (Day | "off" | null)[][] = [];
    for (const w = new Date(start); w <= last; w.setUTCDate(w.getUTCDate() + 7)) {
      weeks.push([0, 1, 2, 3, 4].map((i) => { const d = new Date(w); d.setUTCDate(d.getUTCDate() + i); const iso = d.toISOString().slice(0, 10);
        return iso.slice(0, 7) !== month ? "off" : byDate.get(iso) ?? null; }));
    }
    const ok = list.filter((d): d is Extract<Day, { status: "ok" }> => d.status === "ok");
    out.push({ month, weeks: weeks.filter((w) => w.some((c) => c !== "off")), gain: ok.reduce((a, d) => a + Number(d.gain), 0),
      up: ok.filter((d) => Number(d.gain) > 0).length, down: ok.filter((d) => Number(d.gain) < 0).length, missing: list.length - ok.length });
  }
  return out.sort((a, b) => b.month.localeCompare(a.month));
}

const short = (v: number) => { const a = Math.abs(v); const s = a >= 1e9 ? `${(a / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} tỷ`
  : `${(a / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tr`; return `${v > 0 ? "+" : v < 0 ? "−" : ""}${s}`; };
const pctText = (r: string | null) => (r === null ? "" : `${Number(r) > 0 ? "+" : Number(r) < 0 ? "−" : ""}${formatRatio(r.replace("-", ""), 1)}`);

export function DailyCalendar() {
  const [days, setDays] = useState<Day[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pick, setPick] = useState<string | null>(null);
  useEffect(() => { api<{ days: Day[] }>("performance-daily").then((d) => setDays(d.days), (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const months = days ? monthCalendars(days) : [];
  const chosen = days?.find((d) => d.date === pick) ?? null;
  return (
    <section className="surface" aria-label="Lịch lãi lỗ hằng ngày">
      <h2>Lịch lãi/lỗ hằng ngày</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!days && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {days && (days.length === 0 ? <p className="muted">Chưa có phiên nào từ khi sổ lệnh bắt đầu.</p> : <>
        <div className="dc-legend" aria-hidden="true"><span className="dc-chip dc-r3" />lỗ trên 2%<span className="dc-chip dc-r1" />lỗ nhẹ<span className="dc-chip dc-flat" />đi ngang
          <span className="dc-chip dc-g1" />lãi nhẹ<span className="dc-chip dc-g3" />lãi trên 2%<span className="dc-chip dc-none" />thiếu giá</div>
        <div className="dc-months">{months.map((m) => <div key={m.month} className="dc-month" role="grid" aria-label={`Tháng ${m.month.slice(5)}/${m.month.slice(0, 4)}`}>
          <div className="dc-mhead"><strong>Tháng {Number(m.month.slice(5))}/{m.month.slice(0, 4)}</strong>
            <span className={m.gain > 0 ? "fd-up" : m.gain < 0 ? "fd-down" : undefined}>{short(m.gain)}</span>
            <span className="caption">{m.up} phiên lãi · {m.down} phiên lỗ{m.missing ? ` · ${m.missing} thiếu giá` : ""}</span></div>
          <div className="dc-row dc-wd" role="row">{WEEKDAYS.map((w) => <span key={w} role="columnheader">{w}</span>)}</div>
          {m.weeks.map((w, i) => <div key={i} className="dc-row" role="row">{w.map((d, j) => d === "off" ? <span key={j} className="dc-cell2 dc-off" />
            : d === null ? <span key={j} className="dc-cell2 dc-closed" title="Không có phiên" />
            : <button key={d.date} type="button" role="gridcell" className={`dc-cell2 ${dayTone(d)}${pick === d.date ? " dc-on" : ""}`} onClick={() => setPick(d.date)}
              aria-label={`${dm(d.date)}: ${d.status === "ok" ? `${formatVnd(d.gain)}${d.return ? ` (${formatRatio(d.return, 1)})` : ""}` : "thiếu giá"}`}>
              <span className="dc-day">{Number(d.date.slice(8))}</span><span className="dc-pct">{d.status === "ok" ? pctText(d.return) : "—"}</span></button>)}</div>)}
        </div>)}</div>
        {chosen && <div className="notice" role="note" data-testid="day-detail"><strong>{dm(chosen.date)}:</strong>{" "}
          {chosen.status === "missing" ? `thiếu giá đóng cửa của ${chosen.missing.join(", ")}, chưa tính được.` : <>
            {Number(chosen.gain) >= 0 ? "lãi" : "lỗ"} {formatVnd(chosen.gain.replace("-", ""))}{chosen.return ? ` (${formatRatio(chosen.return, 2)})` : ""}.
            {chosen.tickers.length > 0 && <> Kéo nhiều nhất: {chosen.tickers.map((t) => `${t.symbol} ${Number(t.amount) >= 0 ? "+" : "−"}${formatVnd(t.amount.replace("-", ""))}`).join(", ")}.</>}</>}</div>}
        <p className="caption">Mỗi ô một phiên (số trên là ngày, số dưới là % lãi/lỗ của ngày); tháng mới nhất trước. Lãi/lỗ của ngày = thay đổi giá trị tài khoản chứng khoán trừ tiền nộp/rút trong ngày, theo giá đóng cửa;
          xanh là lãi, đỏ là lỗ, đậm hơn khi biến động lớn (trên 0,7% và 2%). Ô xám là ngày thiếu giá một mã đang nắm. Bấm một ô để xem mã nào kéo nhiều nhất.</p>
      </>)}
    </section>
  );
}
