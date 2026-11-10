"use client";
import { useEffect, useState } from "react";
import { FileSpreadsheet, Save } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";
import { toBase64 } from "./tcbs-import";

type Month = { month: string; income: string; spending: string; saved: string; rate: string | null; passive: string; current: boolean };
type Source = { label: string; group: "business" | "portfolio" | null; passive: boolean };
type Preview = { year: number; months: string[]; warnings: string[]; sources: Source[] };
type View = { version: number; months: Month[]; sources: Source[]; average: { months: string[]; income: string; spending: string; passive: string | null; rate: string | null } | null;
  age: number | null; imported_at: string | null; preview?: Preview };

const label = (key: string) => `${key.slice(5, 7)}/${key.slice(0, 4)}`;
const pct = (v: string | null) => (v === null ? "—" : formatRatio(v, 1).replace(",0%", "%"));

/** Thu chi hằng tháng from the owner's own workbook: they keep writing it in Excel and upload it; only the monthly totals are kept. */
export function Cashflow({ onSaved }: { onSaved?: () => void } = {}) {
  const [view, setView] = useState<View | null>(null);
  const [file, setFile] = useState<{ name: string; content: string } | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("cashflow").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function choose(picked: File | undefined) {
    if (!view || !picked) return;
    setBusy(true); setPreview(null); setMessage(null);
    try {
      const content = toBase64(new Uint8Array(await picked.arrayBuffer()));
      const r = await api<View>("cashflow/import", { method: "POST", body: { content_base64: content, commit: false, expected_version: view.version, request_id: requestId() } });
      setFile({ name: picked.name, content }); setPreview(r.preview ?? null); setView(r);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Không đọc được file."); }
    finally { setBusy(false); }
  }
  async function save() {
    if (!view || !file) return;
    setBusy(true);
    try {
      setView(await api<View>("cashflow/import", { method: "POST", body: { content_base64: file.content, commit: true, expected_version: view.version, request_id: requestId() } }));
      setFile(null); setPreview(null); setMessage(null); onSaved?.();
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
    finally { setBusy(false); }
  }
  const months = view?.months.slice(-12) ?? [];
  const top = Math.max(1, ...months.flatMap((m) => [Number(m.income), Number(m.spending)]));
  const regular = view?.sources.filter((s) => s.passive).map((s) => s.label) ?? [];
  return (
    <section className="surface" aria-label="Thu chi hằng tháng">
      <h2>Thu chi hằng tháng</h2>
      <p className="caption wrap">Bạn vẫn ghi file Excel thu chi như mọi tháng rồi tải lên đây; phần mềm chỉ đọc trang “Tổng” (thu nhập, chi tiêu và thu nhập theo từng nguồn của mỗi tháng), không đọc từng khoản chi hay tên người, và không sửa file. Các tháng này được dùng cho Lạm phát lối sống và Ba mức tự do tài chính.</p>
      <label className="btn"><FileSpreadsheet size={16} aria-hidden="true" />Chọn file Excel thu chi
        <input type="file" accept=".xlsx" className="visually-hidden" aria-label="File Excel thu chi" disabled={!view || busy} onChange={(e) => { void choose(e.target.files?.[0]); e.target.value = ""; }} /></label>
      {message && <p className="errors" role="alert">{message}</p>}
      {preview && file && <div className="notice" data-testid="cf-preview">
        <p><strong>{file.name}</strong>: năm {preview.year}, đọc được {preview.months.length} tháng ({preview.months.map(label).join(", ")}). Lưu sẽ thay các tháng của năm {preview.year} đã có.</p>
        {preview.warnings.map((w) => <p key={w} className="caption">{w}</p>)}
        <button type="button" className="btn primary" disabled={busy || preview.months.length === 0} onClick={() => void save()}><Save size={16} aria-hidden="true" />Lưu vào phần mềm</button>
      </div>}
      {view && view.months.length === 0 && !preview && <p className="muted">Chưa có tháng nào.</p>}
      {view && view.months.length > 0 && <>
        {view.average && <dl className="eb-result">
          <div><dt>Trung bình {view.average.months.length} tháng gần nhất đã xong ({view.average.months.map(label).join(", ")})</dt><dd>thu {formatVnd(view.average.income)} · chi {formatVnd(view.average.spending)}</dd></div>
          <div className="eb-main"><dt>Tỷ lệ tiết kiệm{view.age !== null ? ` (quy tắc: ít nhất ${view.age}% theo tuổi)` : ""}</dt><dd data-testid="cf-rate">{pct(view.average.rate)}</dd></div>
          <div><dt>Thu nhập thụ động thực nhận mỗi tháng</dt><dd data-testid="cf-passive">{view.average.passive === null ? "—" : formatVnd(view.average.passive)}</dd></div>
        </dl>}
        <div className="cf-bars" role="img" aria-label={`Thu nhập và chi tiêu ${months.length} tháng gần nhất`}>
          {months.map((m) => {
            const income = Math.max(Number(m.income), 0), passive = Math.min(Math.max(Number(m.passive), 0), income);
            return <div key={m.month} className="cf-col" title={`${label(m.month)}: thu ${formatVnd(m.income)}, chi ${formatVnd(m.spending)}`}>
              <div className="cf-stack">
                <span className="cf-spend" style={{ bottom: `${(Math.max(Number(m.spending), 0) / top) * 100}%` }} />
                <span className="cf-income" style={{ height: `${((income - passive) / top) * 100}%` }} />
                <span className="cf-passive" style={{ height: `${(passive / top) * 100}%` }} />
              </div>
              <span className="cf-month">{m.month.slice(5, 7)}</span>
            </div>;
          })}
        </div>
        <p className="caption"><span className="gp-swatch cf-key-passive" />thu nhập thụ động · <span className="gp-swatch cf-key-income" />thu nhập khác · <span className="gp-swatch cf-key-spend" />mức chi</p>
        <details className="mc-table"><summary>Xem số liệu theo tháng</summary>
          <div className="tablewrap"><table className="fv-table" aria-label="Thu chi theo tháng">
            <thead><tr><th>Tháng</th><th className="num">Thu nhập</th><th className="num">Chi tiêu</th><th className="num">Tiết kiệm</th><th className="num">% tiết kiệm</th><th className="num">Thụ động</th></tr></thead>
            <tbody>{[...view.months].reverse().map((m) => <tr key={m.month}><td data-label="Tháng">{label(m.month)}{m.current && <span className="pill">đang ghi</span>}</td>
              <td data-label="Thu nhập" className="num">{formatVnd(m.income)}</td><td data-label="Chi tiêu" className="num">{formatVnd(m.spending)}</td>
              <td data-label="Tiết kiệm" className={`num ${Number(m.saved) < 0 ? "negative" : ""}`}>{formatVnd(m.saved)}</td>
              <td data-label="% tiết kiệm" className="num">{m.rate === null ? "—" : <span className={view.age !== null ? (Number(m.rate) * 100 >= view.age ? "positive" : "negative") : undefined}>{pct(m.rate)}</span>}</td>
              <td data-label="Thụ động" className="num">{formatVnd(m.passive)}</td></tr>)}</tbody>
          </table></div>
        </details>
        <p className="caption">Thu nhập thụ động chỉ gồm khoản trả đều: {regular.length ? regular.join(", ") : "chưa có cột nào"}. Lãi bán vàng, cổ phiếu, bất động sản là lãi từng lần nên không tính. Tháng đang ghi không vào trung bình.{view.imported_at ? ` Tải lên lúc ${view.imported_at.slice(11, 16)} ${view.imported_at.slice(8, 10)}/${view.imported_at.slice(5, 7)}/${view.imported_at.slice(0, 4)}.` : ""}</p>
      </>}
    </section>
  );
}
