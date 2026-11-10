"use client";
import { useEffect, useState } from "react";
import { Check, HandCoins, Pencil, Plus, Trash2, X } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd, groupDigitsInput, hanoiDate, parseMoneyInput } from "../lib/format";

type Unit = { id: string; name: string; tenant: string | null; contact: string | null; rent: string | null; due_day: number | null; start: string | null; ends: string | null;
  deposit: string | null; broker: string | null; commission: string | null; note: string | null; track_from?: string | null };
type Payment = { id: string; unit: string; month: string; amount: string; paid_on: string; note: string | null };
type Month = { month: string; due_on: string; got: string; status: "paid" | "short" | "unpaid" | "pending"; owed: string };
type UnitView = { id: string; vacant: boolean; months: Month[]; owed: string; lease_days_left: number | null };
type View = { version: number; book: { units: Unit[]; payments: Payment[] };
  view: { units: UnitView[]; totals: { rent_monthly: string; collected_year: string; owed: string; deposits: string; occupied: number; vacant: number } } };
type Draft = Record<string, string>;

const FIELDS: [keyof Unit, string, "text" | "money" | "int" | "date" | "month"][] = [
  ["name", "Tên phòng", "text"], ["tenant", "Khách thuê", "text"], ["contact", "Liên hệ khách", "text"], ["rent", "Giá thuê mỗi tháng (đ)", "money"],
  ["due_day", "Ngày thu hằng tháng", "int"], ["start", "Ngày bắt đầu hợp đồng", "date"], ["ends", "Ngày hết hợp đồng", "date"], ["deposit", "Tiền cọc (đ)", "money"],
  ["broker", "Môi giới", "text"], ["commission", "Hoa hồng môi giới (đ)", "money"], ["note", "Ghi chú", "text"], ["track_from", "Theo dõi thu tiền từ tháng", "month"]];
const day = (v: string | null | undefined) => (v ? `${v.slice(8, 10)}/${v.slice(5, 7)}/${v.slice(0, 4)}` : "—");
const monthLabel = (m: string) => `${m.slice(5, 7)}/${m.slice(0, 4)}`;

function draftOf(u?: Unit): Draft {
  const d: Draft = Object.fromEntries(FIELDS.map(([k, , kind]) => { const v = u?.[k]; return [k, v === null || v === undefined ? "" : kind === "money" ? groupDigitsInput(String(v)) : String(v)]; }));
  return u ? d : { ...d, track_from: hanoiDate().slice(0, 7) };  // a new room is tracked from this month: earlier rent is in the owner's spreadsheet
}

function MonthPill({ m }: { m: Month | undefined }) {
  if (!m) return <span className="muted">—</span>;
  if (m.status === "paid") return <span className="pill good">đã thu</span>;
  if (m.status === "pending") return <span className="pill">chờ ngày {day(m.due_on).slice(0, 5)}</span>;
  return <span className={`pill ${m.status === "short" ? "warn" : "bad"}`}>{m.status === "short" ? "thu thiếu" : "chưa thu"} {formatVnd(m.owed)}</span>;
}

/** Sổ cho thuê căn hộ: rooms, tenants and leases, the rent received month by month, and what is still owed. Reminders go by Telegram and Việc cần xem. */
export function RentalBook() {
  const [view, setView] = useState<View | null>(null);
  const [editing, setEditing] = useState<{ id: string | null; draft: Draft } | null>(null);
  const [paying, setPaying] = useState<{ unit: string; month: string; amount: string; on: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("rental-book").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function put(units: Unit[], payments: Payment[]): Promise<boolean> {
    if (!view) return false;
    setBusy(true);
    try {
      setView(await api<View>("rental-book", { method: "PUT", body: { units, payments, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      return true;
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); return false; }
    finally { setBusy(false); }
  }
  async function saveUnit() {
    if (!view || !editing) return;
    const d = editing.draft, out: Record<string, unknown> = { id: editing.id ?? requestId() };
    for (const [k, label, kind] of FIELDS) {
      const raw = (d[k] ?? "").trim();
      if (!raw) { if (k === "name") { setMessage("Nhập tên phòng."); return; } out[k] = null; continue; }
      if (kind === "money") { const v = parseMoneyInput(raw); if (v === null || v.includes(".")) { setMessage(`${label}: nhập số đồng.`); return; } out[k] = v; }
      else if (kind === "month") { if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(raw)) { setMessage(`${label}: chọn tháng.`); return; } out[k] = raw; }
      else if (kind === "int") { const n = Number(raw); if (!Number.isInteger(n) || n < 1 || n > 31) { setMessage("Ngày thu từ 1 đến 31."); return; } out[k] = n; }
      else out[k] = raw;
    }
    if (out.deposit === null && out.rent !== null && out.tenant !== null) out.deposit = out.rent;  // the owner's rule: a deposit of one month's rent
    const unit = out as Unit;
    const units = view.book.units.some((u) => u.id === unit.id) ? view.book.units.map((u) => (u.id === unit.id ? unit : u)) : [...view.book.units, unit];
    if (await put(units, view.book.payments)) setEditing(null);
  }
  function startPay(u: Unit, uv: UnitView | undefined) {
    const now = uv?.months.at(-1);
    setMessage(null);
    setPaying({ unit: u.id, month: hanoiDate().slice(0, 7), amount: groupDigitsInput(now && Number(now.owed) > 0 ? now.owed : u.rent ?? ""), on: hanoiDate() });
  }
  async function savePay() {
    if (!view || !paying) return;
    const a = parseMoneyInput(paying.amount);
    if (a === null || a.includes(".") || Number(a) <= 0 || !/^\d{4}-\d{2}$/.test(paying.month) || !paying.on) { setMessage("Nhập tháng, số tiền (đồng, lớn hơn 0) và ngày thu."); return; }
    if (await put(view.book.units, [...view.book.payments, { id: requestId(), unit: paying.unit, month: paying.month, amount: a, paid_on: paying.on, note: null }])) setPaying(null);
  }
  function removeUnit(u: Unit) {
    if (!view || !window.confirm(`Xóa phòng ${u.name} và các lần thu đã ghi của phòng này?`)) return;
    void put(view.book.units.filter((x) => x.id !== u.id), view.book.payments.filter((p) => p.unit !== u.id));
  }
  function removePayment(p: Payment) {
    if (!view || !window.confirm(`Xóa lần thu ${formatVnd(p.amount)} ngày ${day(p.paid_on)}?`)) return;
    void put(view.book.units, view.book.payments.filter((x) => x.id !== p.id));
  }
  const t = view?.view.totals, names = Object.fromEntries((view?.book.units ?? []).map((u) => [u.id, u.name]));
  const locked = !view || busy;
  return (
    <section className="surface db" aria-label="Sổ cho thuê căn hộ">
      <h2>Sổ cho thuê căn hộ</h2>
      <p className="caption wrap">Mỗi phòng: khách, giá thuê, ngày thu và hợp đồng; mỗi lần thu tiền ghi một dòng. Tháng được tính từ ngày bắt đầu hợp đồng hiện tại nhưng không trước tháng bắt đầu theo dõi: tiền thu trước đó nằm trong file Excel, nên tháng chưa ghi ở đây không bị coi là nợ. Phần mềm nhắc ở Việc cần xem và qua Telegram khi quá ngày thu mà chưa đủ tiền, và 30 ngày trước khi hợp đồng hết hạn. Tiền cọc để trống thì lấy bằng 1 tháng tiền thuê.</p>
      {message && !editing && !paying && <p className="errors" role="alert">{message}</p>}
      {t && view.book.units.length > 0 && <div className="kpi-row">
        <div><span className="kpi-label">Tiền thuê mỗi tháng</span><strong>{formatVnd(t.rent_monthly)}</strong><span className="kpi-note">{t.occupied} phòng có khách, {t.vacant} phòng trống</span></div>
        <div><span className="kpi-label">Đã thu năm nay (ghi trong sổ)</span><strong data-testid="rb-collected">{formatVnd(t.collected_year)}</strong><span className="kpi-note">Tiền thu trước khi theo dõi ở đây nằm trong file thu chi</span></div>
        <div><span className="kpi-label">Khách còn nợ</span><strong data-testid="rb-owed" className={Number(t.owed) > 0 ? "negative" : undefined}>{formatVnd(t.owed)}</strong></div>
        <div><span className="kpi-label">Tiền cọc đang giữ</span><strong>{formatVnd(t.deposits)}</strong><span className="kpi-note">Trả lại khách khi hết hợp đồng</span></div>
      </div>}
      {view && view.book.units.length > 0 && <table className="fv-table" aria-label="Các phòng cho thuê">
        <thead><tr><th>Phòng</th><th>Khách</th><th className="num">Giá thuê</th><th>Hợp đồng</th><th>Tháng này</th><th /></tr></thead>
        <tbody>{view.book.units.map((u) => {
          const uv = view.view.units.find((x) => x.id === u.id), now = uv?.months.at(-1);
          return <tr key={u.id}><td data-label="Phòng"><strong>{u.name}</strong></td>
            <td data-label="Khách">{u.tenant ?? <span className="pill">phòng trống</span>}{u.contact ? <div className="caption">{u.contact}</div> : null}</td>
            <td data-label="Giá thuê" className="num">{u.rent ? formatVnd(u.rent) : "—"}{u.due_day ? <div className="caption">thu ngày {u.due_day}</div> : null}</td>
            <td data-label="Hợp đồng">{u.tenant ? <>{day(u.start)} – {day(u.ends)}{uv?.lease_days_left !== null && uv?.lease_days_left !== undefined && uv.lease_days_left <= 30 && uv.lease_days_left >= 0 ? <div><span className="pill warn">còn {uv.lease_days_left} ngày</span></div> : null}</> : "—"}</td>
            <td data-label="Tháng này" data-testid={`rb-now-${u.name}`}>{u.tenant ? <MonthPill m={now && now.month === hanoiDate().slice(0, 7) ? now : undefined} /> : "—"}{uv && Number(uv.owed) > 0 && now && uv.owed !== now.owed ? <div className="caption">tổng nợ {formatVnd(uv.owed)}</div> : null}</td>
            <td className="db-actions">
              {u.tenant && <button type="button" className="btn" aria-label={`Ghi thu phòng ${u.name}`} disabled={locked} onClick={() => startPay(u, uv)}><HandCoins size={14} aria-hidden="true" />Ghi thu</button>}
              <button type="button" className="btn" aria-label={`Sửa phòng ${u.name}`} disabled={locked} onClick={() => { setMessage(null); setEditing({ id: u.id, draft: draftOf(u) }); }}><Pencil size={14} aria-hidden="true" />Sửa</button>
              <button type="button" className="btn" aria-label={`Xóa phòng ${u.name}`} disabled={locked} onClick={() => removeUnit(u)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td></tr>;
        })}</tbody>
      </table>}
      {paying && <form className="eb-form" aria-label="Ghi lần thu tiền thuê" onSubmit={(e) => { e.preventDefault(); void savePay(); }}>
        <strong>Phòng {names[paying.unit]}</strong>
        <label className="field">Tiền thuê của tháng<input type="month" value={paying.month} onChange={(e) => setPaying({ ...paying, month: e.target.value })} /></label>
        <label className="field">Số tiền đã thu (đ)<input inputMode="numeric" value={paying.amount} onChange={(e) => setPaying({ ...paying, amount: groupDigitsInput(e.target.value) })} /></label>
        <label className="field">Ngày thu<input type="date" max={hanoiDate()} value={paying.on} onChange={(e) => setPaying({ ...paying, on: e.target.value })} /></label>
        <button type="submit" className="btn primary" disabled={busy}><Check size={14} aria-hidden="true" />Lưu lần thu</button>
        <button type="button" className="btn" onClick={() => { setPaying(null); setMessage(null); }}><X size={14} aria-hidden="true" />Hủy</button>
        {message && <p className="errors" role="alert">{message}</p>}
      </form>}
      {editing && <form className="pv-form" aria-label="Thông tin phòng" onSubmit={(e) => { e.preventDefault(); void saveUnit(); }}>
        <div className="formgrid">{FIELDS.map(([k, label, kind]) => <label key={k} className="field">{label}
          <input type={kind === "date" ? "date" : kind === "month" ? "month" : "text"} inputMode={kind === "money" || kind === "int" ? "numeric" : undefined} value={editing.draft[k] ?? ""}
            placeholder={k === "deposit" ? "trống = 1 tháng tiền thuê" : k === "tenant" ? "trống = phòng trống" : undefined}
            onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, [k]: kind === "money" ? groupDigitsInput(e.target.value) : e.target.value } })} /></label>)}</div>
        {message && <p className="errors" role="alert">{message}</p>}
        <div className="actions"><button type="submit" className="btn primary" disabled={busy}><Check size={14} aria-hidden="true" />Lưu phòng</button>
          <button type="button" className="btn" onClick={() => { setEditing(null); setMessage(null); }}><X size={14} aria-hidden="true" />Hủy</button></div>
      </form>}
      <button type="button" className="btn" disabled={locked || editing !== null} onClick={() => { setMessage(null); setEditing({ id: null, draft: draftOf() }); }}><Plus size={14} aria-hidden="true" />Thêm phòng</button>
      {view && view.book.payments.length > 0 && <details className="mc-table"><summary>Lịch sử thu tiền ({view.book.payments.length} lần)</summary>
        <div className="tablewrap"><table className="fv-table" aria-label="Lịch sử thu tiền thuê">
          <thead><tr><th>Ngày thu</th><th>Phòng</th><th>Tháng</th><th className="num">Số tiền</th><th /></tr></thead>
          <tbody>{[...view.book.payments].sort((a, b) => b.paid_on.localeCompare(a.paid_on)).slice(0, 60).map((p) => <tr key={p.id}><td data-label="Ngày thu">{day(p.paid_on)}</td>
            <td data-label="Phòng">{names[p.unit]}</td><td data-label="Tháng">{monthLabel(p.month)}</td><td data-label="Số tiền" className="num">{formatVnd(p.amount)}</td>
            <td className="db-actions"><button type="button" className="btn" aria-label={`Xóa lần thu ngày ${day(p.paid_on)} phòng ${names[p.unit]}`} disabled={locked} onClick={() => removePayment(p)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td></tr>)}</tbody>
        </table></div>
      </details>}
    </section>
  );
}
