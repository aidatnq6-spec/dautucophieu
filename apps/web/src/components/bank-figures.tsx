"use client";
import { useEffect, useState } from "react";
import { FileSearch, Pencil, Save, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio } from "../lib/format";

const FIELDS = ["group1", "group2", "group3", "group4", "group5", "demand_deposits", "margin_deposits", "customer_deposits", "car"] as const;
type Field = (typeof FIELDS)[number];
// A quarter's figures can come from two files (statements, and the separate CAR report): each field keeps its file and page.
type Source = { kind: "manual" } | { kind: "pdf"; url: string | null; pages: Partial<Record<Field, number>>; urls?: Partial<Record<Field, string>> };
type Quarter = { quarter: string; values: Record<Field, string | null>; source: Source;
  derived: { npl: string | null; group2_ratio: string | null; casa: string | null; car: string | null } };
type View = { symbol: string; version: number; quarters: Quarter[]; labels: Record<Field, string> };
type Read = { url: string; fields: Partial<Record<Field, { value: string; page: number }>>; missing: Field[]; warnings: string[] };

const pct = (v: string | null) => (v ? formatRatio(v, 2) : "—");
const blank = () => Object.fromEntries(FIELDS.map((f) => [f, ""])) as Record<Field, string>;
const toInput = (v: string | null) => (v ?? "").replace(".", ",");
/** Typed number to a plain decimal: "537.304,578" (Vietnamese), "537.304" (thousands) and "537304.578" (decimal point) all read right. */
export function fromInput(raw: string): string {
  const v = raw.trim().replace(/\s/g, "");
  if (v.includes(",")) return v.replace(/\./g, "").replace(",", ".");
  return /^\d{1,3}(\.\d{3})+$/.test(v) ? v.replace(/\./g, "") : v;
}

const sourceFiles = (s: Extract<Source, { kind: "pdf" }>) => [...new Set([...Object.values(s.urls ?? {}), ...(s.url ? [s.url] : [])])];
const fileName = (u: string | null | undefined) => (u ? decodeURIComponent(u.split("/").pop() ?? "PDF") : "PDF");

/** Owner-entered bank figures per quarter (loans by group, deposits, CAR), with a PDF reader that only proposes values. */
export function BankFigures({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [hidden, setHidden] = useState(false);
  const [quarter, setQuarter] = useState("");
  const [values, setValues] = useState(blank);
  const [source, setSource] = useState<Source>({ kind: "manual" });
  const [url, setUrl] = useState("");
  const [read, setRead] = useState<Read | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>(`bank-figures/${encodeURIComponent(symbol)}`).then(setView, (e) => {
      if (e instanceof ApiError && e.failure.code === "not_a_watched_bank") setHidden(true); else setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
    });
  }, [symbol]);
  if (hidden) return null;

  function edit(q: Quarter) {
    setQuarter(q.quarter); setValues(Object.fromEntries(FIELDS.map((f) => [f, toInput(q.values[f])])) as Record<Field, string>);
    setSource(q.source); setRead(null); setMessage(null);
  }
  async function readPdf() {
    if (!url.trim()) { setMessage("Dán đường dẫn https của file PDF báo cáo."); return; }
    setBusy(true);
    try {
      const r = await api<Read>(`bank-figures/${encodeURIComponent(symbol)}/read-pdf`, { method: "POST", body: { url: url.trim(), request_id: requestId() } });
      setRead(r);
      setValues((old) => ({ ...old, ...Object.fromEntries(Object.entries(r.fields).map(([f, x]) => [f, toInput(x!.value)])) }));
      setSource((old) => {
        const before = old.kind === "pdf" ? old : { pages: {}, urls: {} };
        const found = Object.entries(r.fields);
        return { kind: "pdf", url: r.url, pages: { ...before.pages, ...Object.fromEntries(found.map(([f, x]) => [f, x!.page])) },
          urls: { ...(before.urls ?? {}), ...Object.fromEntries(found.map(([f]) => [f, r.url])) } };
      });
      setUrl("");
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi đọc file."); } finally { setBusy(false); }
  }
  async function save() {
    if (!view) return;
    if (!/^\d{4}-Q[1-4]$/.test(quarter.trim())) { setMessage("Nhập quý theo dạng 2026-Q3."); return; }
    try {
      setView(await api<View>(`bank-figures/${encodeURIComponent(symbol)}/${quarter.trim()}`, { method: "PUT",
        body: { values: Object.fromEntries(FIELDS.map((f) => [f, values[f].trim() ? fromInput(values[f]) : null])), source,
          expected_version: view.version, request_id: requestId() } }));
      setQuarter(""); setValues(blank()); setSource({ kind: "manual" }); setRead(null); setUrl(""); setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  async function remove(q: string) {
    if (!view || !window.confirm(`Xóa số liệu ${q}?`)) return;
    try {
      setView(await api<View>(`bank-figures/${encodeURIComponent(symbol)}/${q}/delete`, { method: "POST",
        body: { expected_version: view.version, request_id: requestId() } }));
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi xóa."); }
  }
  const pages = source.kind === "pdf" ? source.pages : {};
  return (
    <section className="surface" aria-label="Số liệu ngân hàng">
      <h2>Số liệu ngân hàng (nhập tay)</h2>
      <p className="caption">Nợ nhóm 1–5, tiền gửi và CAR không có ở nguồn miễn phí: nhập từ thuyết minh báo cáo tài chính quý (tỷ đồng), hoặc dán đường dẫn PDF
        công khai để phần mềm đọc và điền sẵn — kiểm tra lại rồi mới lưu. CASA = (không kỳ hạn + ký quỹ) / tiền gửi khách hàng. Có số của hai quý cùng kỳ thì
        Điểm sức khỏe thêm tiêu chí CASA tăng và nợ nhóm 2 giảm.</p>
      {view && view.quarters.length > 0 && <table className="fv-table" aria-label={`Số liệu ngân hàng ${symbol}`}>
        <thead><tr><th>Quý</th><th className="num">NPL</th><th className="num">Nợ nhóm 2</th><th className="num">CASA</th><th className="num">CAR</th><th>Nguồn</th><th /></tr></thead>
        <tbody>{view.quarters.map((q) => <tr key={q.quarter}>
          <td data-label="Quý">{q.quarter}</td><td data-label="NPL" className="num">{pct(q.derived.npl)}</td>
          <td data-label="Nợ nhóm 2" className="num">{pct(q.derived.group2_ratio)}</td><td data-label="CASA" className="num">{pct(q.derived.casa)}</td>
          <td data-label="CAR" className="num">{pct(q.derived.car)}</td>
          <td data-label="Nguồn">{q.source.kind === "pdf" ? sourceFiles(q.source).map((u, i) => <a key={u} href={u} target="_blank" rel="noreferrer">
            {i ? " · " : ""}PDF {i + 1}</a>) : "Nhập tay"}</td>
          <td className="actions"><button type="button" className="btn" aria-label={`Sửa ${q.quarter}`} onClick={() => edit(q)}><Pencil size={14} aria-hidden="true" />Sửa</button>
            <button type="button" className="btn" aria-label={`Xóa ${q.quarter}`} onClick={() => void remove(q.quarter)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td>
        </tr>)}</tbody>
      </table>}
      <div className="fv-search">
        <label className="field">Đường dẫn PDF báo cáo (https)<input type="url" value={url} placeholder="https://…/bctc-quy-3-2026.pdf" disabled={!view}
          onChange={(e) => setUrl(e.target.value)} /></label>
        <button type="button" className="btn" disabled={!view || busy} onClick={() => void readPdf()}><FileSearch size={16} aria-hidden="true" />
          {busy ? "Đang đọc…" : "Đọc và điền sẵn"}</button>
      </div>
      {read && <div className="notice" role="status">Đã điền {Object.keys(read.fields).length}/{FIELDS.length} ô từ PDF — kiểm tra lại với file trước khi lưu.
        {read.missing.length > 0 && <> Chưa tìm thấy: {read.missing.map((f) => view?.labels[f] ?? f).join(", ")}.</>}
        {read.warnings.map((w) => <div key={w}>{w}</div>)}</div>}
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <label className="field">Quý<input value={quarter} placeholder="2026-Q3" maxLength={7} disabled={!view} onChange={(e) => setQuarter(e.target.value)} /></label>
        {FIELDS.map((f) => <label key={f} className="field">{view?.labels[f] ?? f}{f === "car" ? "" : " (tỷ đồng)"}
          <input inputMode="decimal" value={values[f]} disabled={!view} onChange={(e) => setValues({ ...values, [f]: e.target.value })} />
          {pages[f] && <span className="caption">trang {pages[f]} trong {fileName(source.kind === "pdf" ? source.urls?.[f] ?? source.url : null)}</span>}</label>)}
        <button type="submit" className="btn primary" disabled={!view}><Save size={16} aria-hidden="true" />Lưu quý này</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
    </section>
  );
}
