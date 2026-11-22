"use client";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";

export type Item = { id: string; label: string; auto: boolean; done: boolean | null; detail: string | null };
type Open = { open: true; version: number; year: number; items: Item[]; left: number };
type Closed = { open: false; opens_on: string };

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** How an item stands: the app's checks say what they found, an unreadable one says so (never counted as done). */
export function itemState(i: Item): { text: string; tone: "good" | "warn" | "" } {
  if (i.done === true) return { text: i.auto ? "đã xong (tự kiểm)" : "đã xong", tone: "good" };
  if (i.done === null) return { text: "chưa kiểm được", tone: "" };
  return { text: i.auto ? "chưa xong (tự kiểm)" : "chưa xong", tone: "warn" };
}

/** Việc cuối năm (owner, 22/11/2026): open 1 December to 31 January; reminders go in Việc tài chính hôm nay on 1/12, 20/12 and 5/1. */
export function YearEnd() {
  const [view, setView] = useState<Open | Closed | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<Open | Closed>("year-end").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function tick(item: Item) {
    if (!view || !view.open) return;
    try {
      setView(await api<Open>("year-end/tick", { method: "POST", body: { item: item.id, done: !item.done, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  return (
    <section className="surface" aria-label="Việc cuối năm">
      <h2>Việc cuối năm{view && view.open ? ` ${view.year}` : ""}</h2>
      {message && <p className="errors" role="alert">{message}</p>}
      {!view && !message && <p className="muted" role="status">Đang tải…</p>}
      {view && !view.open && <p className="caption">Danh sách mở từ {dmy(view.opens_on)} đến hết tháng 1 năm sau.</p>}
      {view && view.open && <>
        <p className="caption">{view.left ? `Còn ${view.left} việc.` : "Đã xong mọi việc."} Việc có nhãn tự kiểm do phần mềm đọc từ số đã lưu; việc
          còn lại bạn tự đánh dấu. Nhắc trong Việc tài chính hôm nay ngày 01/12, 20/12 và 05/01 khi còn việc.</p>
        <ul className="ye-list">{view.items.map((i) => {
          const s = itemState(i);
          return (
            <li key={i.id}>
              {i.auto ? <span className={`pill ${s.tone}`}>{s.text}</span>
                : <label><input type="checkbox" checked={i.done === true} onChange={() => tick(i)} /> <span className={`pill ${s.tone}`}>{s.text}</span></label>}
              {" "}<strong>{i.label}</strong>{i.detail && <span className="caption"> · {i.detail}</span>}
            </li>
          );
        })}</ul>
      </>}
    </section>
  );
}
