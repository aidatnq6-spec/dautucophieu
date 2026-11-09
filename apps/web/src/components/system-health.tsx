"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Problem = { id: string; label: string; detail: string };
type Source = { id: string; label: string; last: string | null; max_days: number; stale: boolean };
type Step = { step: string; last_at: string; exit: number; failing: number };
type Health = { ok: boolean; problems: Problem[]; sources: Source[]; steps: Step[]; last_finish: string | null; drill: { at: string; ok: boolean; backup: string; files: number; error: string | null } | null };

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" }) : "—");

/** Whether the unattended work is really happening: failing steps, data gone stale, the after-close run, the restore drill. */
export function SystemHealth() {
  const [h, setH] = useState<Health | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<Health>("system-health").then(setH, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Tình trạng hệ thống">
      <h2>Tình trạng hệ thống</h2>
      <p className="caption">Phần chạy tự động có đang làm việc không. Sự cố mới và lúc hồi phục được báo một lần qua Telegram (khi đã bật gửi tự động). Nếu máy tắt thì không có gì chạy và không báo được.</p>
      {message && <p className="errors" role="alert">{message}</p>}
      {!h && !message && <p className="muted" role="status">Đang kiểm tra…</p>}
      {h && <>
        {h.ok ? <p className="notice" role="status">Mọi thứ đang chạy bình thường.</p> : <ul className="errors" aria-label="Sự cố">{h.problems.map((p) => <li key={p.id}><strong>{p.label}</strong>: {p.detail}</li>)}</ul>}
        <p className="caption">Lượt sau phiên xong gần nhất: {when(h.last_finish)} · Diễn tập khôi phục: {h.drill ? `${when(h.drill.at)}, ${h.drill.ok ? `đạt (${h.drill.files} tệp)` : "không đạt"}` : "chưa có"}</p>
        <div className="tablewrap"><table aria-label="Độ mới của dữ liệu">
          <thead><tr><th>Nguồn</th><th>Cập nhật lần cuối</th><th className="num">Cho phép</th><th>Trạng thái</th></tr></thead>
          <tbody>{h.sources.map((s) => <tr key={s.id}><td>{s.label}</td><td>{when(s.last)}</td><td className="num">{s.max_days} ngày</td><td className={s.stale ? "negative" : "positive"}>{s.stale ? "Quá hạn" : "Mới"}</td></tr>)}</tbody>
        </table></div>
        <details className="mc-table"><summary>Các bước tự động ({h.steps.length})</summary>
          <div className="tablewrap"><table aria-label="Các bước tự động">
            <thead><tr><th>Bước</th><th>Lần chạy cuối</th><th className="num">Mã thoát</th><th className="num">Lỗi liên tiếp</th></tr></thead>
            <tbody>{h.steps.map((s) => <tr key={s.step}><td>{s.step}</td><td>{when(s.last_at)}</td><td className="num">{s.exit}</td><td className="num">{s.failing}</td></tr>)}</tbody>
          </table></div>
        </details>
      </>}
    </section>
  );
}
