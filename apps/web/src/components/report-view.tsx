"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";
import { HoldingsTable, type HoldingRow } from "./holdings-table";
import { ACTION_LABEL, NOTE_TEXT, REASON_TEXT, label } from "./labels";
import { REPORT_STATUS } from "./reports-list";

type Report = { report_id: string; session_date: string; generated_at: string; status: string; provenance: string;
  decision: { action: string; headline: string; reasons: string[] }; holdings: HoldingRow[];
  items: { entity_id: string; action: string; reasons: string[]; source_ids: string[] }[];
  ledger_summary: { cash: string; realized_gain: string; dividend_income: string; net_contributions: string };
  narrative: { source: string; text: string }; verification_flags: string[]; previous_report_id: string | null; sources: string[] };

const SEND_STATUS: Record<string, string> = {
  sent: "Đã gửi", disabled: "Chưa bật gửi Telegram trong Cài đặt.", not_publishable: "Bản tin chưa phát hành nên không gửi.",
  unknown: "Chưa rõ kết quả một phần đã gửi; kiểm tra nhóm Telegram trước khi gửi lại.", failed: "Gửi thất bại; xem nhóm Telegram và thử lại sau.",
};

function TelegramPanel({ reportId, publishable }: { reportId: string; publishable: boolean }) {
  const [parts, setParts] = useState<string[] | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async (work: () => Promise<void>) => {
    setBusy(true); setFailure(null);
    try { await work(); } catch (e) { setFailure(e instanceof ApiError ? e.failure.message : "Có lỗi xảy ra."); } finally { setBusy(false); }
  };
  const preview = () => run(async () => {
    setParts((await api<{ parts: string[] }>("notifications/preview", { method: "POST", body: { report_id: reportId } })).parts);
  });
  const send = () => {
    if (!window.confirm("Gửi thật bản tin này tới nhóm Telegram đã cấu hình? Mọi thành viên nhóm sẽ thấy giá trị danh mục.")) return;
    void run(async () => {
      const r = await api<{ status: string; parts_sent: number; parts_total: number }>("notifications/test-send",
        { method: "POST", body: { report_id: reportId, confirm: true } });
      setResult(r.status === "sent" ? `Đã gửi ${r.parts_sent}/${r.parts_total} phần tới Telegram.` : SEND_STATUS[r.status] ?? r.status);
    });
  };
  return (
    <section aria-label="Telegram">
      <h2>Telegram</h2>
      {!publishable && <p className="caption">Chỉ bản tin đã phát hành mới gửi được.</p>}
      <div className="actions">
        <button className="btn" disabled={busy} onClick={() => void preview()}>Xem trước tin Telegram</button>
        <button className="btn primary" disabled={busy || !publishable} onClick={send}>Gửi thử tới Telegram</button>
      </div>
      {failure && <p className="errors" role="alert">{failure}</p>}
      {result && <p className="notice" role="status">{result}</p>}
      {parts && <div role="region" aria-label="Xem trước Telegram">
        {parts.map((t, i) => <pre key={i} style={{ whiteSpace: "pre-wrap" }}>{parts.length > 1 && <span className="caption">Phần {i + 1}/{parts.length}{"\n"}</span>}{t}</pre>)}</div>}
    </section>
  );
}

export function ReportView({ reportId }: { reportId: string }) {
  const [r, setR] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Report>(`reports/${encodeURIComponent(reportId)}`).then(setR, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [reportId]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!r) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  return (
    <article className="surface brief" style={{ maxWidth: 880, margin: "0 auto", padding: "32px 40px" }}>
      <div className="row"><h1 style={{ fontFamily: "Georgia, 'Times New Roman', serif", margin: 0 }}>Bản tin phiên {r.session_date}</h1>
        <span className={`pill ${r.status === "published" ? "good" : "warn"}`}>{REPORT_STATUS[r.status] ?? r.status}</span></div>
      <p className="caption">Ngày phiên {r.session_date} · tạo lúc {new Date(r.generated_at).toLocaleString("vi-VN")} · dữ liệu {r.provenance}
        {r.previous_report_id && <> · <Link href={`/reports/${r.previous_report_id}`}>bản trước cùng phạm vi</Link></>}</p>
      {r.status !== "published" && <p className="notice">Bản tin chưa đủ dữ liệu: không gửi Telegram và không dùng để ra quyết định mới.</p>}
      <h2>Kết luận</h2>
      <p><strong>{r.decision.headline}</strong></p>
      <ul>{r.decision.reasons.map((x) => <li key={x}>{label(REASON_TEXT, x)}</li>)}</ul>
      <h2>Danh mục</h2>
      <p>Tiền trong sổ {formatVnd(r.ledger_summary.cash)} · lãi/lỗ đã thực hiện {formatVnd(r.ledger_summary.realized_gain)} · cổ tức ròng {formatVnd(r.ledger_summary.dividend_income)}</p>
      <HoldingsTable rows={r.holdings} />
      <h2>Cơ hội và cảnh báo</h2>
      <ul>{r.items.map((i) => <li key={i.entity_id}><strong>{i.entity_id}</strong>: {label(ACTION_LABEL, i.action)} — {i.reasons.map((x) => label(REASON_TEXT, x)).join("; ")}</li>)}</ul>
      <h2>Nhận định {r.narrative.source === "ai" ? "(AI, đã kiểm tra)" : "(số liệu đã kiểm chứng, không dùng AI)"}</h2>
      <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.85 }}>{r.narrative.text}</p>
      <h2>Kiểm tra dữ liệu</h2>
      <ul>{r.verification_flags.map((f) => <li key={f}>{NOTE_TEXT(f)}</li>)}</ul>
      {r.sources.length > 0 && <p className="caption">Nguồn: {r.sources.join(", ")}</p>}
      <TelegramPanel reportId={r.report_id} publishable={r.status === "published"} />
    </article>
  );
}
