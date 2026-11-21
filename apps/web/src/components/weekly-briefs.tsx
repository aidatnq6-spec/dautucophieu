"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Week = { week: string; sent_at: string };
type Brief = Week & { text: string };

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const sentAt = (iso: string) => new Date(iso).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });

/** Bản tin tuần: the notes exactly as Telegram took them, one a week, newest first. */
export function WeeklyBriefs() {
  const [weeks, setWeeks] = useState<Week[] | null>(null);
  const [shown, setShown] = useState<Brief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fail = (e: unknown) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
  useEffect(() => {
    api<{ weeks: Week[]; latest: Brief | null }>("weekly-briefs").then((d) => { setWeeks(d.weeks); setShown(d.latest); }, fail);
  }, []);
  const open = (week: string) => { setError(null); api<Brief>(`weekly-briefs/${week}`).then(setShown, fail); };
  return (
    <section className="surface" aria-label="Bản tin tuần">
      <h2>Bản tin tuần</h2>
      <p className="caption">Đúng nội dung đã gửi Telegram vào cuối tuần, lưu từ 21/11/2026. Chỉ để theo dõi, không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!weeks && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {weeks && weeks.length === 0 && <p className="muted">Chưa có bản tin tuần nào được lưu. Bản tin gửi vào sáng thứ Bảy.</p>}
      {weeks && weeks.length > 0 && <>
        <label className="field wb-pick">Tuần
          <select aria-label="Chọn tuần" value={shown?.week ?? ""} onChange={(e) => open(e.target.value)}>
            {weeks.map((w) => <option key={w.week} value={w.week}>Tuần kết thúc {dmy(w.week)}</option>)}
          </select>
        </label>
        {shown && <>
          <p className="caption">Gửi lúc {sentAt(shown.sent_at)}.</p>
          <pre className="wb-text" aria-label="Nội dung bản tin tuần">{shown.text}</pre>
        </>}
      </>}
    </section>
  );
}
