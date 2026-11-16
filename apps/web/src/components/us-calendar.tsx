"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

export type UsEvent = { kind: "fomc" | "minutes" | "cpi"; on: string; at: string; text: string; source: string };
type Data = { updated_on: string | null; events: UsEvent[] };

/** "10/12 · 02:00" and how many days away, from the event's Vietnam date and today's. */
export function whenText(e: Pick<UsEvent, "on" | "at">, today: string): string {
  const day = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
  const days = Math.round((day(e.on) - day(today)) / 86400000);
  return `${e.on.slice(8, 10)}/${e.on.slice(5, 7)} · ${e.at} (${days === 0 ? "hôm nay" : days === 1 ? "ngày mai" : `còn ${days} ngày`})`;
}

/** Lịch vĩ mô Mỹ: the Fed's decisions and minutes and the CPI releases, read from the Fed's and BLS's own calendars. */
export function UsCalendar({ today }: { today: string }) {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Data>("macro/us-calendar").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Lịch vĩ mô Mỹ">
      <h2>Lịch vĩ mô Mỹ (60 ngày tới)</h2>
      <p className="caption">Quyết định lãi suất và biên bản họp FOMC theo lịch của Fed, ngày công bố CPI theo lịch của BLS; giờ đã đổi sang giờ Việt Nam.
        Ứng dụng đọc lại mỗi ngày và nhắc qua Telegram trước một ngày. Biên bản chỉ hiện khi Fed đã ghi ngày trên lịch.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!d && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {d && (d.events.length ? <ul className="bm-list" aria-label="Sự kiện vĩ mô Mỹ sắp tới">{d.events.map((e) => (
        <li key={`${e.kind}-${e.on}-${e.at}`}><strong>{whenText(e, today)}</strong>: {e.text}{" "}
          <a className="caption" href={e.source} target="_blank" rel="noreferrer">nguồn</a></li>))}</ul>
        : <p className="muted">{d.updated_on ? "Không có sự kiện nào trong 60 ngày tới." : "Chưa đọc được lịch (lượt chạy sau phiên sẽ đọc)."}</p>)}
    </section>
  );
}
