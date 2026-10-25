"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { ApiError, api } from "../lib/api";

type Row = { report_id: string; report_kind: string; session_date: string; generated_at: string; status: string; provenance: string };
export const REPORT_STATUS: Record<string, string> = { building: "Đang tạo", validated: "Đã kiểm tra", published: "Đã phát hành", incomplete: "Thiếu dữ liệu",
  failed: "Lỗi", superseded: "Đã thay thế" };
const MAX_POLLS = 30;

export function ReportsList() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [session, setSession] = useState(() => new Date().toISOString().slice(0, 10));
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const stop = useRef(false);
  const load = useCallback(() => api<{ reports: Row[] }>("reports").then((r) => setRows(r.reports), (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")), []);
  // Reset on (re)mount: React may run cleanup then the effect again, and polling must survive that.
  useEffect(() => { stop.current = false; void load(); return () => { stop.current = true; }; }, [load]);

  async function create() {
    setError(null);
    try {
      const { job_id } = await api<{ job_id: string }>("jobs/after-close", { method: "POST", body: { session_date: session } });
      for (let i = 0; i < MAX_POLLS && !stop.current; i++) {
        const job = await api<{ status: string; stages: string[] }>(`jobs/${job_id}`);
        setProgress(`${REPORT_STATUS[job.status] ?? job.status}${job.stages.length ? ` · ${job.stages.join(" → ")}` : ""}`);
        if (!["accepted", "running"].includes(job.status)) { await load(); return; }
        await new Promise((r) => setTimeout(r, 2000));
      }
      setProgress("Đã ngừng theo dõi; tác vụ vẫn có thể đang chạy ở máy chủ. Tải lại trang để xem kết quả.");
    } catch (e) { setError(e instanceof ApiError ? e.failure.message : "Không tạo được bản tin."); }
  }

  return (
    <>
      <section className="surface">
        <h2>Tạo bản tin sau phiên</h2>
        <div className="formgrid"><label className="field">Ngày phiên<input type="date" value={session} onChange={(e) => setSession(e.target.value)} /></label></div>
        <div className="actions"><button className="btn primary" onClick={() => void create()}><RefreshCw size={16} aria-hidden="true" />Tạo bản tin</button></div>
        {progress && <p role="status">{progress}</p>}
        {error && <p className="errors" role="alert">{error}</p>}
      </section>
      <section className="surface">
        <h2>Các bản tin</h2>
        {!rows ? <p className="muted">Đang tải…</p> : rows.length === 0 ? <p className="muted">Chưa có bản tin.</p> : (
          <ul>{rows.map((r) => (
            <li key={r.report_id}><Link href={`/reports/${r.report_id}`}>Phiên {r.session_date}</Link> · <span className="pill">{REPORT_STATUS[r.status] ?? r.status}</span>
              {" "}<span className="caption">tạo lúc {new Date(r.generated_at).toLocaleString("vi-VN")}{r.provenance !== "licensed" ? ` · dữ liệu ${r.provenance}` : ""}</span></li>))}</ul>
        )}
      </section>
    </>
  );
}
