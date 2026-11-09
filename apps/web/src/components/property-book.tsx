"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Calculator, Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";

type Row = Record<string, string | number | null> & { id: string; name: string };
type Book = { properties: Row[]; loans: Row[]; ceiling: string };
type Picture = { financial: string | null; property_total: string; property_missing: string[]; stale: string[]; debt: string; debt_missing: string[]; payments: string; payments_missing: string[];
  rent: string; rent_less_payments: string | null; loans: Record<string, string | null>; ceiling: string; complete: boolean; total_assets: string | null; net_worth: string | null;
  liquid_share: string | null; clear_share: string | null; unclear_share: string | null; property_share: string | null; debt_ratio: string | null; over: boolean; yields: Record<string, string | null>; live_total: string | null; invest_total: string | null; invest_property_total: string | null;
  live_share: string | null; invest_share: string | null; invest_property_of_invest: string | null; financial_of_invest: string | null };
type View = { version: number; book: Book; picture: Picture; financial_reason: string | null; unpriced: string[] };
type List = "properties" | "loans";
type Draft = Record<string, string>;
type Editing = { list: List; draft: Draft; isNew: boolean } | null;
type Field = { key: string; label: string; type: "text" | "money" | "date" | "percent" | "int" | "select"; options?: [string, string][]; blank?: boolean };

const KIND: [string, string][] = [["home", "Nhà ở"], ["apartment", "Căn hộ"], ["land", "Đất"], ["other", "Khác"]];
const PURPOSE: [string, string][] = [["live", "Để ở"], ["rent", "Cho thuê"], ["invest", "Đầu tư"]];
const LEGAL: [string, string][] = [["certificate", "Có sổ"], ["contract", "Hợp đồng mua bán"], ["unknown", "Chưa rõ"]];
const METHOD: [string, string][] = [["declining", "Dư nợ giảm dần"], ["annuity", "Trả đều hàng tháng"]];
const label = (options: [string, string][], v: unknown) => options.find(([k]) => k === v)?.[1] ?? "—";

const PROPERTY_FIELDS: Field[] = [
  { key: "name", label: "Tên bất động sản", type: "text" }, { key: "kind", label: "Loại", type: "select", options: KIND }, { key: "purpose", label: "Mục đích", type: "select", options: PURPOSE },
  { key: "value", label: "Giá trị tự ước tính (đ)", type: "money" }, { key: "valued_on", label: "Ngày ước tính", type: "date" }, { key: "legal", label: "Pháp lý", type: "select", options: LEGAL },
  { key: "rent_monthly", label: "Tiền thuê mỗi tháng (đ)", type: "money" }, { key: "cost", label: "Giá mua (đ)", type: "money" }, { key: "bought_year", label: "Năm mua", type: "int" },
];
const loanFields = (properties: Row[]): Field[] => [
  { key: "name", label: "Tên khoản vay", type: "text" }, { key: "bank", label: "Ngân hàng", type: "text" }, { key: "balance", label: "Dư nợ hiện tại (đ)", type: "money" }, { key: "balance_on", label: "Ngày cập nhật dư nợ", type: "date" },
  { key: "rate", label: "Lãi hiện tại (%/năm)", type: "percent" }, { key: "promo_ends", label: "Ngày hết ưu đãi", type: "date" }, { key: "after_rate", label: "Lãi sau ưu đãi (%/năm)", type: "percent" },
  { key: "months_left", label: "Số tháng còn lại", type: "int" }, { key: "method", label: "Cách trả", type: "select", options: METHOD },
  { key: "collateral", label: "Thế chấp bằng", type: "select", blank: true, options: properties.map((p) => [p.id, p.name]) },
];
const DEFAULTS: Record<List, Draft> = { properties: { kind: "home", purpose: "live", legal: "unknown" }, loans: { method: "declining" } };

function toDraft(fields: Field[], row: Row): Draft {
  return Object.fromEntries(fields.map((f) => {
    const v = row[f.key];
    if (v === null || v === undefined) return [f.key, ""];
    return [f.key, f.type === "money" ? groupDigitsInput(String(v)) : f.type === "percent" ? String(v).replace(".", ",") : String(v)];
  }));
}

function toRow(fields: Field[], draft: Draft, id: string): { ok: Row } | { error: string } {
  const out: Row = { id, name: "" };
  for (const f of fields) {
    const raw = (draft[f.key] ?? "").trim();
    if (raw === "") { if (f.key === "name") return { error: "Nhập tên." }; out[f.key] = null; continue; }
    if (f.type === "money") { const v = parseMoneyInput(raw); if (v === null || v.includes(".")) return { error: `${f.label}: nhập số đồng.` }; out[f.key] = v; }
    else if (f.type === "percent") { const v = parseMoneyInput(raw); if (v === null) return { error: `${f.label}: chưa đọc được.` }; out[f.key] = v; }
    else if (f.type === "int") { if (!/^\d+$/.test(raw)) return { error: `${f.label}: nhập số nguyên.` }; out[f.key] = Number(raw); }
    else out[f.key] = raw;
  }
  return { ok: out };
}

const money = (v: string | number | null | undefined) => (v === null || v === undefined ? "Chưa nhập" : formatVnd(String(v)));
const share = (v: string | null) => (v === null ? "—" : formatRatio(v, 1));

function RowForm({ fields, draft, onDraft, onSave, onCancel, busy, error }: { fields: Field[]; draft: Draft; onDraft: (d: Draft) => void; onSave: () => void; onCancel: () => void; busy: boolean; error: string | null }) {
  const set = (key: string, value: string) => onDraft({ ...draft, [key]: value });
  return (
    <form className="pv-form" onSubmit={(e) => { e.preventDefault(); onSave(); }}>
      <div className="formgrid">{fields.map((f) => <label key={f.key} className="field">{f.label}
        {f.type === "select"
          ? <select value={draft[f.key] ?? ""} onChange={(e) => set(f.key, e.target.value)}>{f.blank && <option value="">Không có</option>}{f.options!.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          : f.type === "date" ? <input type="date" value={draft[f.key] ?? ""} onChange={(e) => set(f.key, e.target.value)} />
            : <input inputMode={f.type === "text" ? undefined : f.type === "percent" ? "decimal" : "numeric"} value={draft[f.key] ?? ""} onChange={(e) => set(f.key, f.type === "money" ? groupDigitsInput(e.target.value) : e.target.value)} />}
      </label>)}</div>
      {error && <p className="errors" role="alert">{error}</p>}
      <div className="actions"><button type="submit" className="btn primary" disabled={busy}><Check size={14} aria-hidden="true" />Lưu</button>
        <button type="button" className="btn" onClick={onCancel}><X size={14} aria-hidden="true" />Hủy</button></div>
    </form>
  );
}

/** Bất động sản và khoản vay, and what the owner has and owes altogether. Values are the owner's estimates; nothing here reaches Tháp tài sản. */
export function PropertyBook() {
  const [view, setView] = useState<View | null>(null);
  const [editing, setEditing] = useState<Editing>(null);
  const [ceiling, setCeiling] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("property-book").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);

  async function put(book: Book): Promise<boolean> {
    if (!view) return false;
    setBusy(true);
    try {
      setView(await api<View>("property-book", { method: "PUT", body: { ...book, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      return true;
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); return false; }
    finally { setBusy(false); }
  }
  const fieldsOf = (list: List) => (list === "properties" ? PROPERTY_FIELDS : loanFields(view?.book.properties ?? []));
  async function saveRow() {
    if (!view || !editing) return;
    const id = editing.draft.id || requestId();
    const r = toRow(fieldsOf(editing.list), editing.draft, id);
    if ("error" in r) { setMessage(r.error); return; }
    const rows = view.book[editing.list];
    const next = editing.isNew ? [...rows, r.ok] : rows.map((x) => (x.id === id ? r.ok : x));
    if (await put({ ...view.book, [editing.list]: next })) setEditing(null);
  }
  async function remove(list: List, row: Row) {
    if (!view || !window.confirm(`Xóa "${row.name}"?`)) return;
    const loans = list === "properties" ? view.book.loans.map((x) => (x.collateral === row.id ? { ...x, collateral: null } : x)) : view.book.loans;
    await put({ ...view.book, loans, [list]: view.book[list].filter((x) => x.id !== row.id) });
  }
  async function saveCeiling() {
    if (!view || ceiling === null) return;
    const v = parseMoneyInput(ceiling);
    if (v === null || Number(v) <= 0 || Number(v) > 100) { setMessage("Ngưỡng cảnh báo từ trên 0 đến 100%."); return; }
    if (await put({ ...view.book, ceiling: v })) setCeiling(null);
  }
  const start = (list: List, row?: Row) => { setMessage(null); setCeiling(null); setEditing(row ? { list, draft: { ...toDraft(fieldsOf(list), row), id: row.id }, isNew: false } : { list, draft: { ...DEFAULTS[list] }, isNew: true }); };
  const locked = !view || busy || editing !== null;
  const p = view?.picture;
  const actions = (list: List, row: Row) => <td className="db-actions">
    {list === "loans" && p?.loans[row.id] && <Link className="btn" aria-label={`Mở ${row.name} ở Tính khoản vay`} href={`/loan?loan=${row.id}`}><Calculator size={14} aria-hidden="true" />Tính</Link>}
    <button type="button" className="btn" disabled={locked} aria-label={`Sửa ${row.name}`} onClick={() => start(list, row)}><Pencil size={14} aria-hidden="true" />Sửa</button>
    <button type="button" className="btn" disabled={locked} aria-label={`Xóa ${row.name}`} onClick={() => void remove(list, row)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td>;
  const form = (list: List) => editing?.list === list && <RowForm fields={fieldsOf(list)} draft={editing.draft} busy={busy} error={message}
    onDraft={(draft) => setEditing({ ...editing, draft: { ...draft, ...(editing.draft.id ? { id: editing.draft.id } : {}) } })} onSave={() => void saveRow()} onCancel={() => { setEditing(null); setMessage(null); }} />;
  return (
    <section className="surface db" aria-label="Bất động sản và khoản vay">
      <h2>Bất động sản và khoản vay</h2>
      <p className="caption wrap">Bức tranh gồm tài sản tài chính, bất động sản và các khoản nợ. Giá trị bất động sản do bạn tự ước tính, phần mềm không tự lấy giá nhà. Ô để trống là chưa nhập, không tính bằng 0. Phần này không ảnh hưởng Tháp tài sản hay số tiền dành cho cổ phiếu.</p>
      {message && !editing && <p className="errors" role="alert">{message}</p>}
      {p && <>
        <div className="kpi-row">
          <div><span className="kpi-label">Tài sản ròng</span><strong data-testid="nw-net">{p.net_worth === null ? "Chưa đủ số" : formatVnd(p.net_worth)}</strong></div>
          <div><span className="kpi-label">Tài sản tài chính</span><strong data-testid="nw-financial">{p.financial === null ? "Chưa có" : formatVnd(p.financial)}</strong><span className="kpi-note">Các lớp Tháp tài sản, cổ phiếu theo giá thị trường nên tổng khác Tháp (dùng giá vốn)</span></div>
          <div><span className="kpi-label">Bất động sản</span><strong>{formatVnd(p.property_total)}</strong><span className="kpi-note">Tự ước tính</span></div>
          <div><span className="kpi-label">Tổng dư nợ</span><strong data-testid="nw-debt">{formatVnd(p.debt)}</strong>{p.debt_ratio !== null && <span className="kpi-note">{share(p.debt_ratio)} tổng tài sản</span>}</div>
          <div><span className="kpi-label">Khoản trả tháng này</span><strong>{formatVnd(p.payments)}</strong><span className="kpi-note">Theo lãi hiện tại{p.rent_less_payments !== null && Number(p.rent) > 0 ? ` · thu thuê ${formatVnd(p.rent)}` : ""}</span></div>
        </div>
        {p.complete && p.total_assets !== "0" && <dl className="ln-flow">
          <div><dt>Tài sản tài chính (dễ bán)</dt><dd>{share(p.liquid_share)}</dd></div>
          <div><dt>Bất động sản đã rõ pháp lý</dt><dd>{share(p.clear_share)}</dd></div>
          <div><dt>Bất động sản chưa rõ pháp lý</dt><dd>{share(p.unclear_share)}</dd></div>
          {p.rent_less_payments !== null && <div><dt>Tiền thuê trừ khoản trả</dt><dd className={Number(p.rent_less_payments) < 0 ? "negative" : undefined}>{formatVnd(p.rent_less_payments)}</dd></div>}
        </dl>}
        {p.live_total !== null && p.total_assets !== "0" && <section aria-label="Cấu trúc tài sản">
          <h3>Cấu trúc tài sản</h3>
          <dl className="ln-flow">
            <div><dt>Để ở (không tạo ra tiền)</dt><dd data-testid="nw-live">{formatVnd(p.live_total)} · {share(p.live_share)}</dd></div>
            <div><dt>Đầu tư (tài chính, bất động sản cho thuê và đầu tư)</dt><dd data-testid="nw-invest">{formatVnd(p.invest_total!)} · {share(p.invest_share)}</dd></div>
            {p.invest_property_of_invest !== null && <div><dt>Trong phần đầu tư: bất động sản / tài chính</dt><dd data-testid="nw-mix">{share(p.invest_property_of_invest)} / {share(p.financial_of_invest)}</dd></div>}
          </dl>
        </section>}
        {view.financial_reason && <p className="notice pv-note" data-testid="nw-reason">{view.financial_reason}</p>}
        {p.over && <p className="notice pv-note" data-testid="nw-over">Bất động sản chiếm {share(p.property_share)} tổng tài sản, vượt ngưỡng {String(p.ceiling).replace(".", ",")}% bạn đặt.</p>}
        {p.property_missing.length > 0 && <p className="notice pv-note">Chưa có giá trị: {p.property_missing.join(", ")}. Chưa tính được tài sản ròng.</p>}
        {p.debt_missing.length > 0 && <p className="notice pv-note">Chưa có dư nợ: {p.debt_missing.join(", ")}. Chưa tính được tài sản ròng.</p>}
        {p.payments_missing.length > 0 && <p className="notice pv-note">Chưa tính được khoản trả, cần dư nợ, lãi và số tháng còn lại: {p.payments_missing.join(", ")}.</p>}
        {p.stale.length > 0 && <p className="notice pv-note" data-testid="nw-stale">Giá trị quá 6 tháng hoặc chưa có ngày ước tính, nên cập nhật: {p.stale.join(", ")}.</p>}
        {view.unpriced.length > 0 && <p className="notice pv-note">Chưa có giá nên chưa tính vào tài sản tài chính: {view.unpriced.join(", ")}.</p>}
      </>}
      <h3>Bất động sản</h3>
      {view && view.book.properties.length > 0 && <table className="fv-table" aria-label="Bất động sản">
        <thead><tr><th>Tên</th><th>Loại</th><th>Mục đích</th><th className="num">Giá trị tự ước tính</th><th>Ngày ước tính</th><th>Pháp lý</th><th className="num">Tiền thuê/tháng</th><th className="num">Lợi suất cho thuê</th><th /></tr></thead>
        <tbody>{view.book.properties.map((r) => <tr key={r.id}><td data-label="Tên">{r.name}</td><td data-label="Loại">{label(KIND, r.kind)}</td><td data-label="Mục đích">{label(PURPOSE, r.purpose)}</td>
          <td data-label="Giá trị" className="num">{money(r.value)}</td><td data-label="Ngày ước tính">{r.valued_on ?? "Chưa nhập"}</td><td data-label="Pháp lý">{label(LEGAL, r.legal)}</td>
          <td data-label="Tiền thuê" className="num">{r.rent_monthly === null ? "—" : money(r.rent_monthly)}</td>
          <td data-label="Lợi suất cho thuê" className="num">{p?.yields[r.id] ? `${formatRatio(p.yields[r.id]!, 2)}/năm` : "—"}</td>{actions("properties", r)}</tr>)}</tbody>
      </table>}
      {form("properties")}
      <button type="button" className="btn" disabled={locked} onClick={() => start("properties")}><Plus size={14} aria-hidden="true" />Thêm bất động sản</button>
      <h3>Khoản vay</h3>
      {view && view.book.loans.length > 0 && <table className="fv-table" aria-label="Khoản vay">
        <thead><tr><th>Tên</th><th className="num">Dư nợ</th><th className="num">Lãi hiện tại</th><th className="num">Tháng còn lại</th><th>Cách trả</th><th className="num">Khoản trả tháng này</th><th /></tr></thead>
        <tbody>{view.book.loans.map((r) => <tr key={r.id}><td data-label="Tên">{r.name}{r.bank ? <div className="caption">{r.bank}</div> : null}</td><td data-label="Dư nợ" className="num">{money(r.balance)}</td>
          <td data-label="Lãi hiện tại" className="num">{r.rate === null ? "Chưa nhập" : `${String(r.rate).replace(".", ",")}%`}{r.promo_ends ? <div className="caption">hết ưu đãi {r.promo_ends}</div> : null}</td><td data-label="Tháng còn lại" className="num">{r.months_left ?? "Chưa nhập"}</td><td data-label="Cách trả">{label(METHOD, r.method)}</td>
          <td data-label="Khoản trả" className="num">{p?.loans[r.id] ? formatVnd(p.loans[r.id]!) : "Chưa đủ số"}</td>{actions("loans", r)}</tr>)}</tbody>
      </table>}
      {form("loans")}
      <button type="button" className="btn" disabled={locked} onClick={() => start("loans")}><Plus size={14} aria-hidden="true" />Thêm khoản vay</button>
      <h3>Ngưỡng cảnh báo</h3>
      {ceiling === null
        ? <div className="db-reserve"><span>Cảnh báo khi bất động sản vượt <strong data-testid="nw-ceiling">{view ? String(view.book.ceiling).replace(".", ",") : ""}%</strong> tổng tài sản. Mức bạn tự đặt, không phải chuẩn nào cả.</span>
          <button type="button" className="btn" disabled={locked} onClick={() => { setMessage(null); setCeiling(String(view!.book.ceiling).replace(".", ",")); }}><Pencil size={14} aria-hidden="true" />Sửa</button></div>
        : <form className="db-reserve" onSubmit={(e) => { e.preventDefault(); void saveCeiling(); }}><label className="field">Ngưỡng cảnh báo bất động sản (% tổng tài sản)<input inputMode="decimal" value={ceiling} onChange={(e) => setCeiling(e.target.value)} /></label>
          <button type="submit" className="btn primary" disabled={busy}>Lưu</button><button type="button" className="btn" onClick={() => { setCeiling(null); setMessage(null); }}>Hủy</button></form>}
    </section>
  );
}
