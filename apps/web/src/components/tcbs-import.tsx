"use client";
import { useState } from "react";
import { FileUp } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd } from "../lib/format";
import { LEDGER_ERRORS } from "./transaction-form";

type Row = { line: number; symbol: string; type: "buy" | "sell"; date: string; quantity: number; price: string; fee: string; tax: string; status: "new" | "already" | "manual" | "before_opening" };
type Preview = { version: number; rows: Row[]; counts: Record<Row["status"], number>; blocked: { code: string; message: string; symbol: string | null; date: string | null } | null; problems: { line: number; message: string }[] };

const STATUS: Record<Row["status"], string> = { new: "Sẽ thêm", already: "Đã nhập trước đó", manual: "Đã có trong sổ (ghi tay)", before_opening: "Trước số dư đầu kỳ, bỏ qua" };
const MAX_BYTES = 700_000;

export function toBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}

const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** A TCInvest order history into Sổ giao dịch: read, shown line by line, and written only on confirmation, all or none. */
export function TcbsImport({ onDone }: { onDone: () => void }) {
  const [content, setContent] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fail = (e: unknown, fallback: string) => setMessage(e instanceof ApiError ? LEDGER_ERRORS[e.failure.code] ?? e.failure.message : fallback);
  const reset = () => { setContent(null); setPreview(null); };
  async function choose(file: File | undefined) {
    if (!file) return;
    reset(); setMessage(null);
    if (file.size > MAX_BYTES) { setMessage("File quá lớn (tối đa khoảng 700 KB). Hãy xuất từng khoảng thời gian ngắn hơn."); return; }
    setBusy(true);
    try {
      const text = toBase64(new Uint8Array(await file.arrayBuffer()));
      setPreview(await api<Preview>("ledger/import-tcbs", { method: "POST", body: { content_base64: text, expected_version: 0, request_id: requestId() } }));
      setContent(text);
    } catch (e) { fail(e, "Không đọc được file."); } finally { setBusy(false); }
  }
  async function commit() {
    if (!content || !preview) return;
    setBusy(true);
    try {
      await api("ledger/import-tcbs", { method: "POST", body: { content_base64: content, commit: true, expected_version: preview.version, request_id: requestId() } });
      const added = preview.counts.new;
      reset(); setMessage(`Đã thêm ${added} lệnh vào sổ.`); onDone();
    } catch (e) { fail(e, "Lỗi lưu."); } finally { setBusy(false); }
  }
  return (
    <details className="surface" aria-label="Nhập sao kê TCBS">
      <summary><strong>Nhập sao kê TCBS (Excel)</strong></summary>
      <p className="caption">Trên TCInvest, tải Lịch sử giao dịch cổ phiếu ra Excel rồi chọn file ở đây. Phần mềm cho xem trước từng lệnh, chưa ghi gì cho tới khi bạn xác nhận. Lệnh đã nhập, hoặc đã ghi tay trùng ngày, mã, loại, khối lượng và giá, không bị thêm lần nữa. Nếu sổ không chứa nổi các lệnh này thì không ghi lệnh nào.</p>
      <div className="actions"><label className="btn"><FileUp size={16} aria-hidden="true" />Chọn file
        <input type="file" accept=".xlsx" aria-label="Chọn file sao kê TCBS" hidden disabled={busy} onChange={(e) => { void choose(e.target.files?.[0]); e.target.value = ""; }} /></label></div>
      {preview && <div role="status">
        <p><strong>{preview.counts.new}</strong> lệnh mới · {preview.counts.already} đã nhập · {preview.counts.manual} đã ghi tay · {preview.counts.before_opening} trước số dư đầu kỳ · <strong>{preview.problems.length}</strong> dòng lỗi</p>
        {preview.blocked && <p className="errors" role="alert">{preview.blocked.symbol ? `${preview.blocked.symbol} ngày ${day(preview.blocked.date ?? "")}: ` : ""}{preview.blocked.message} Chưa ghi lệnh nào.</p>}
        {preview.problems.length > 0 && <ul className="ft-checks" aria-label="Dòng lỗi sao kê">{preview.problems.map((p) => <li key={p.line}>Dòng {p.line}: {p.message}</li>)}</ul>}
        {preview.rows.length > 0 && <div className="tablewrap"><table aria-label="Xem trước sao kê">
          <thead><tr><th>Ngày</th><th>Lệnh</th><th>Mã</th><th className="num">Khối lượng</th><th className="num">Giá khớp</th><th className="num">Phí</th><th className="num">Thuế</th><th>Xử lý</th></tr></thead>
          <tbody>{preview.rows.map((r) => <tr key={r.line}><td>{day(r.date)}</td><td>{r.type === "buy" ? "Mua" : "Bán"}</td><td>{r.symbol}</td><td className="num">{r.quantity.toLocaleString("vi-VN")}</td>
            <td className="num">{formatVnd(r.price)}</td><td className="num">{formatVnd(r.fee)}</td><td className="num">{formatVnd(r.tax)}</td><td>{STATUS[r.status]}</td></tr>)}</tbody></table></div>}
        <div className="actions">
          {preview.counts.new > 0 && !preview.blocked && <button type="button" className="btn primary" disabled={busy} onClick={() => void commit()}>Thêm {preview.counts.new} lệnh vào sổ</button>}
          <button type="button" className="btn" onClick={reset}>Hủy</button></div>
      </div>}
      {message && <p className="notice" role="status">{message}</p>}
    </details>
  );
}
