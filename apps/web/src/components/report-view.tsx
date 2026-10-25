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

export function ReportView({ reportId }: { reportId: string }) {
  const [r, setR] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Report>(`reports/${encodeURIComponent(reportId)}`).then(setR, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [reportId]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!r) return <p className="muted">Đang tải…</p>;
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
    </article>
  );
}
