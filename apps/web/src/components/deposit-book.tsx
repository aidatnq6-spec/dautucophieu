"use client";
import { useEffect, useState, type ReactNode } from "react";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";

type Account = { id: string; name: string; amount: string; liquid: boolean };
type Deposit = { id: string; bank: string; matures: string; principal: string; rate: string | null; interest: string | null;
  payout: "end" | "upfront"; locked: boolean };
type Holding = { id: string; name: string; amount: string };
type Bond = Holding & { rate: string | null };
type Holdings = { bonds: Bond[]; gold: Holding[]; crypto: Holding[] };
type Month = { month: string; count: number; principal: string; interest: string; missing_interest: number };
type Liquidity = { now: string; ledger_cash: string; ledger_cash_counted: boolean; accounts_liquid: string; reserve: string; status: "enough" | "short"; short: string | null;
  maturing_90d: string; not_now: { accounts: string; locked: string; unlocked: string; overdue: string } };
type View = { version: number; book: { accounts: Account[]; deposits: Deposit[]; count_ledger_cash: boolean; reserve: string | null } & Holdings;
  calendar: { months: Month[]; due_soon: string[]; overdue: string[] }; liquidity: Liquidity; profile_reserve: string };

/** Rows as typed: money grouped with dots, rate with a comma, blanks kept blank. */
export type AccountDraft = Account;
export type DepositDraft = Omit<Deposit, "rate" | "interest"> & { rate: string; interest: string };
export type HoldingDraft = Holding;
export type BondDraft = Holding & { rate: string };
type HoldingDrafts = { bonds: BondDraft[]; gold: HoldingDraft[]; crypto: HoldingDraft[] };
const NO_HOLDINGS: HoldingDrafts = { bonds: [], gold: [], crypto: [] };

const money = (v: string) => formatVnd(v, { unit: false });
const toAccountDraft = (a: Account): AccountDraft => ({ ...a, amount: money(a.amount) });
const toDepositDraft = (d: Deposit): DepositDraft => ({ ...d, principal: money(d.principal), interest: d.interest === null ? "" : money(d.interest),
  rate: d.rate === null ? "" : d.rate.replace(".", ",") });
const whole = (raw: string) => { const v = parseMoneyInput(raw); return v !== null && !v.includes(".") ? v : null; };
const toHoldingDrafts = (b: Holdings): HoldingDrafts => ({
  bonds: b.bonds.map((x) => ({ ...x, amount: money(x.amount), rate: x.rate === null ? "" : x.rate.replace(".", ",") })),
  gold: b.gold.map((x) => ({ ...x, amount: money(x.amount) })), crypto: b.crypto.map((x) => ({ ...x, amount: money(x.amount) })) });
const LIST_NAME = { bonds: "Trái phiếu", gold: "Vàng", crypto: "Tiền số" } as const;

/** The book the API takes, or the first row that cannot be saved, named by its place in the table. Blank rate or interest = unknown (null). */
export function bookPayload(accounts: AccountDraft[], deposits: DepositDraft[], holdings: HoldingDrafts = NO_HOLDINGS):
  { ok: { accounts: Account[]; deposits: Deposit[] } & Holdings } | { error: string } {
  const outAccounts: Account[] = [];
  for (const [i, a] of accounts.entries()) {
    if (!a.name.trim()) return { error: `Tài khoản ${i + 1}: nhập tên.` };
    const amount = whole(a.amount);
    if (amount === null) return { error: `Tài khoản ${i + 1}: nhập số tiền (đồng).` };
    outAccounts.push({ id: a.id, name: a.name.trim(), amount, liquid: a.liquid });
  }
  const outDeposits: Deposit[] = [];
  for (const [i, d] of deposits.entries()) {
    const n = `Sổ ${i + 1}`;
    if (!d.bank.trim()) return { error: `${n}: nhập tên ngân hàng.` };
    if (!d.matures) return { error: `${n}: chọn ngày đáo hạn.` };
    const principal = whole(d.principal);
    if (principal === null || principal === "0") return { error: `${n}: nhập tiền gốc (đồng, lớn hơn 0).` };
    const rate = d.rate.trim() ? parseMoneyInput(d.rate) : null;
    if (d.rate.trim() && (rate === null || Number(rate) > 30)) return { error: `${n}: lãi suất từ 0 đến 30%/năm, hoặc để trống.` };
    const interest = d.interest.trim() ? whole(d.interest) : null;
    if (d.interest.trim() && interest === null) return { error: `${n}: lãi dự kiến là số đồng, hoặc để trống.` };
    outDeposits.push({ id: d.id, bank: d.bank.trim(), matures: d.matures, principal, rate, interest, payout: d.payout, locked: d.locked });
  }
  const out: Holdings = { bonds: [], gold: [], crypto: [] };
  for (const list of ["bonds", "gold", "crypto"] as const) {
    for (const [i, h] of holdings[list].entries()) {
      const n = `${LIST_NAME[list]} ${i + 1}`;
      if (!h.name.trim()) return { error: `${n}: nhập tên.` };
      const amount = whole(h.amount);
      if (amount === null) return { error: `${n}: nhập số tiền (đồng).` };
      if (list !== "bonds") { out[list].push({ id: h.id, name: h.name.trim(), amount }); continue; }
      const raw = (h as BondDraft).rate.trim();
      const rate = raw ? parseMoneyInput(raw) : null;
      if (raw && (rate === null || Number(rate) > 30)) return { error: `${n}: lợi suất từ 0 đến 30%/năm, hoặc để trống.` };
      out.bonds.push({ id: h.id, name: h.name.trim(), amount, rate });
    }
  }
  return { ok: { accounts: outAccounts, deposits: outDeposits, ...out } };
}

/** Quỹ dự phòng as typed: whole đồng, or blank = the confirmed profile's figure (null). */
export function reservePayload(raw: string): { ok: string | null } | { error: string } {
  if (!raw.trim()) return { ok: null };
  const v = whole(raw.trim());
  return v === null ? { error: "Quỹ dự phòng: nhập số đồng, hoặc để trống để theo hồ sơ." } : { ok: v };
}

/** The rows with this one saved: an edited row keeps its place, a new one goes last. */
export function upsertRow<T extends { id: string }>(rows: T[], row: T): T[] {
  return rows.some((r) => r.id === row.id) ? rows.map((r) => (r.id === row.id ? row : r)) : [...rows, row];
}

export function removeRow<T extends { id: string }>(rows: T[], id: string): T[] {
  return rows.filter((r) => r.id !== id);
}

type Drafts = { accounts: AccountDraft[]; deposits: DepositDraft[] } & HoldingDrafts;
type ListKey = keyof Drafts;
type AnyDraft = AccountDraft | DepositDraft | HoldingDraft | BondDraft;
type Editing = { list: ListKey; draft: AnyDraft; isNew: boolean } | null;
type Field = { key: string; label: string; aria: string; kind: "text" | "money" | "rate" | "date" | "check" | "payout"; max?: number;
  optional?: boolean; yes?: string; no?: string };

const NAME_FIELD = (max: number): Field => ({ key: "name", label: "Tên", aria: "Tên", kind: "text", max });
const AMOUNT: Field = { key: "amount", label: "Số tiền (đ)", aria: "Số tiền", kind: "money" };
const FIELDS: Record<ListKey, Field[]> = {
  accounts: [NAME_FIELD(60), AMOUNT, { key: "liquid", label: "Rút ngay", aria: "Rút ngay", kind: "check", yes: "rút ngay", no: "chưa rút được" }],
  deposits: [{ key: "bank", label: "Ngân hàng", aria: "Ngân hàng", kind: "text", max: 40 },
    { key: "matures", label: "Đáo hạn", aria: "Ngày đáo hạn", kind: "date" },
    { key: "principal", label: "Gốc (đ)", aria: "Tiền gốc", kind: "money" },
    { key: "rate", label: "Lãi suất %/năm", aria: "Lãi suất", kind: "rate", optional: true },
    { key: "interest", label: "Lãi dự kiến (đ)", aria: "Lãi dự kiến", kind: "money", optional: true },
    { key: "payout", label: "Trả lãi", aria: "Cách trả lãi", kind: "payout" },
    { key: "locked", label: "Phong tỏa", aria: "Phong tỏa đến hạn", kind: "check", yes: "phong tỏa", no: "không" }],
  bonds: [NAME_FIELD(80), AMOUNT, { key: "rate", label: "Lợi suất %/năm", aria: "Lợi suất", kind: "rate", optional: true }],
  gold: [NAME_FIELD(80), AMOUNT],
  crypto: [NAME_FIELD(80), AMOUNT],
};
const TABLE_NAME: Record<ListKey, string> = { accounts: "Tài khoản tiền mặt", deposits: "Sổ tiền gửi", ...LIST_NAME };
const ROW_NAME: Record<ListKey, string> = { accounts: "tài khoản", deposits: "sổ", bonds: "trái phiếu", gold: "vàng", crypto: "tiền số" };
const ADD_LABEL: Record<ListKey, string> = { accounts: "Thêm tài khoản", deposits: "Thêm sổ", bonds: "Thêm dòng trái phiếu", gold: "Thêm dòng vàng",
  crypto: "Thêm dòng tiền số" };
const MAX_ROWS: Record<ListKey, number> = { accounts: 30, deposits: 100, bonds: 30, gold: 30, crypto: 30 };
const EMPTY: Record<ListKey, () => AnyDraft> = {
  accounts: () => ({ id: requestId(), name: "", amount: "", liquid: true }),
  deposits: () => ({ id: requestId(), bank: "", matures: "", principal: "", rate: "", interest: "", payout: "end", locked: true }),
  bonds: () => ({ id: requestId(), name: "", amount: "", rate: "" }),
  gold: () => ({ id: requestId(), name: "", amount: "" }),
  crypto: () => ({ id: requestId(), name: "", amount: "" }),
};
const toDrafts = (b: View["book"]): Drafts => ({ accounts: b.accounts.map(toAccountDraft), deposits: b.deposits.map(toDepositDraft), ...toHoldingDrafts(b) });
const field = (row: AnyDraft, key: string) => (row as unknown as Record<string, string | boolean>)[key];

/** A saved value as read: a blank rate or interest is "chưa nhập", never 0. */
function shown(f: Field, v: string | boolean) {
  if (f.kind === "check") return v ? f.yes : <span className="muted">{f.no}</span>;
  if (f.kind === "payout") return v === "upfront" ? "Đầu kỳ (đã nhận)" : "Cuối kỳ";
  const text = String(v);
  if (!text) return <span className="muted">chưa nhập</span>;
  if (f.kind === "money") return `${text} đ`;
  if (f.kind === "rate") return `${text}%`;
  if (f.kind === "date") return `${text.slice(8)}/${text.slice(5, 7)}/${text.slice(0, 4)}`;
  return text;
}

function FieldInput({ f, value, label, onChange }: { f: Field; value: string | boolean; label: string; onChange: (v: string | boolean) => void }) {
  const aria = `${f.aria} ${label}`;
  if (f.kind === "check") return <input type="checkbox" aria-label={aria} checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />;
  if (f.kind === "payout") return <select aria-label={aria} value={String(value)} onChange={(e) => onChange(e.target.value)}>
    <option value="end">Cuối kỳ</option><option value="upfront">Đầu kỳ (đã nhận)</option></select>;
  if (f.kind === "date") return <input type="date" aria-label={aria} value={String(value)} onChange={(e) => onChange(e.target.value)} />;
  if (f.kind === "money") return <input aria-label={aria} inputMode="numeric" placeholder={f.optional ? "chưa nhập" : undefined} value={String(value)}
    onChange={(e) => onChange(groupDigitsInput(e.target.value))} />;
  if (f.kind === "rate") return <input aria-label={aria} inputMode="decimal" placeholder="chưa nhập" value={String(value)} onChange={(e) => onChange(e.target.value)} />;
  return <input aria-label={aria} maxLength={f.max} value={String(value)} onChange={(e) => onChange(e.target.value)} />;
}

/** One list of Sổ tài sản: each saved row read-only with Sửa and Xóa; the row being edited (or added) as inputs with Lưu and Hủy. */
function RowTable({ list, rows, editing, locked, status, onEdit, onDraft, onSave, onCancel, onDelete }: {
  list: ListKey; rows: AnyDraft[]; editing: Editing; locked: boolean; status: (id: string) => ReactNode;
  onEdit: (row: AnyDraft) => void; onDraft: (row: AnyDraft) => void; onSave: () => void; onCancel: () => void; onDelete: (row: AnyDraft, n: number) => void }) {
  const fields = FIELDS[list];
  const mine = editing?.list === list ? editing : null;
  const all = mine?.isNew ? [...rows, mine.draft] : rows;
  if (!all.length) return <p className="caption">Chưa có dòng nào.</p>;
  return (
    <table className="fv-table db-table" aria-label={TABLE_NAME[list]}>
      <thead><tr>{fields.map((f) => <th key={f.key}>{f.label}</th>)}<th /></tr></thead>
      <tbody>{all.map((r, i) => {
        const draft = mine && mine.draft.id === r.id ? mine.draft : null;
        const label = `${ROW_NAME[list]} ${i + 1}`;
        return (
          <tr key={r.id} className={draft ? "db-editing" : undefined}>
            {fields.map((f) => <td key={f.key} data-label={f.aria}>
              {draft ? <FieldInput f={f} label={label} value={field(draft, f.key)} onChange={(v) => onDraft({ ...draft, [f.key]: v } as AnyDraft)} />
                : <>{shown(f, field(r, f.key))}{f.kind === "date" && status(r.id)}</>}</td>)}
            <td className="db-actions">{draft ? <>
              <button type="button" className="btn primary" disabled={locked} onClick={onSave}><Check size={14} aria-hidden="true" />Lưu</button>
              <button type="button" className="btn" disabled={locked} onClick={onCancel}><X size={14} aria-hidden="true" />Hủy</button>
            </> : <>
              <button type="button" className="btn" aria-label={`Sửa ${label}`} disabled={locked || editing !== null} onClick={() => onEdit(r)}>
                <Pencil size={14} aria-hidden="true" />Sửa</button>
              <button type="button" className="btn" aria-label={`Xóa ${label}`} disabled={locked || editing !== null} onClick={() => onDelete(r, i + 1)}>
                <Trash2 size={14} aria-hidden="true" />Xóa</button>
            </>}</td>
          </tr>
        );
      })}</tbody>
    </table>
  );
}

const monthLabel = (m: string) => `${m.slice(5)}/${m.slice(0, 4)}`;

/** Sổ tài sản: cash accounts, term deposits, bonds, gold and crypto; the months deposits come back, and cash now against the reserve.
 * A sổ not yet due is never cash now; one past its date is overdue, not guessed as rolled over or closed. Each Lưu or Xóa saves the
 * whole book at once, so Tháp tài sản recomputes. */
export function DepositBook({ onSaved }: { onSaved?: () => void }) {
  const [view, setView] = useState<View | null>(null);
  const [editing, setEditing] = useState<Editing>(null);
  const [reserveDraft, setReserveDraft] = useState<string | null>(null);  // null = not editing the reserve
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("deposit-book").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const saved = view ? toDrafts(view.book) : null;

  async function put(drafts: Drafts, countLedger: boolean, reserve: string | null): Promise<boolean> {
    if (!view) return false;
    const r = bookPayload(drafts.accounts, drafts.deposits, drafts);
    if ("error" in r) { setMessage(r.error); return false; }
    setBusy(true);
    try {
      setView(await api<View>("deposit-book", { method: "PUT", body: { ...r.ok, count_ledger_cash: countLedger, reserve, expected_version: view.version,
        request_id: requestId() } }));
      setMessage(null);
      onSaved?.();
      return true;
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); return false; }
    finally { setBusy(false); }
  }
  async function saveRow() {
    if (!view || !saved || !editing) return;
    const next = { ...saved, [editing.list]: upsertRow(saved[editing.list] as AnyDraft[], editing.draft) } as Drafts;
    if (await put(next, view.book.count_ledger_cash, view.book.reserve)) setEditing(null);
  }
  async function deleteRow(list: ListKey, row: AnyDraft, n: number) {
    if (!view || !saved || !window.confirm(`Xóa ${ROW_NAME[list]} ${n}? Sổ tài sản lưu ngay và Tháp tài sản tính lại.`)) return;
    await put({ ...saved, [list]: removeRow(saved[list] as AnyDraft[], row.id) } as Drafts, view.book.count_ledger_cash, view.book.reserve);
  }
  async function saveReserve(raw: string | null) {
    if (!view || !saved) return;
    const r = raw === null ? { ok: null } : reservePayload(raw);
    if ("error" in r) { setMessage(r.error); return; }
    if (await put(saved, view.book.count_ledger_cash, r.ok)) setReserveDraft(null);
  }
  const cancel = () => { setEditing(null); setReserveDraft(null); setMessage(null); };
  const locked = !view || busy;
  const status = (id: string) => view?.calendar.overdue.includes(id) ? <span className="pill bad">quá hạn, cần cập nhật</span>
    : view?.calendar.due_soon.includes(id) ? <span className="pill warn">sắp đến hạn</span> : null;
  const alert = message && <p className="errors" role="alert">{message}</p>;
  const table = (list: ListKey) => saved && <>
    <RowTable list={list} rows={saved[list] as AnyDraft[]} editing={editing} locked={locked} status={status}
      onEdit={(row) => { setReserveDraft(null); setMessage(null); setEditing({ list, draft: row, isNew: false }); }}
      onDraft={(draft) => setEditing({ list, draft, isNew: editing?.isNew ?? false })}
      onSave={() => void saveRow()} onCancel={cancel} onDelete={(row, n) => void deleteRow(list, row, n)} />
    {editing?.list === list && alert}
    <button type="button" className="btn" disabled={locked || editing !== null || saved[list].length >= MAX_ROWS[list]}
      onClick={() => { setReserveDraft(null); setMessage(null); setEditing({ list, draft: EMPTY[list](), isNew: true }); }}>
      <Plus size={14} aria-hidden="true" />{ADD_LABEL[list]}</button>
  </>;
  const l = view?.liquidity;
  const reserve = view?.book.reserve ?? null;
  return (
    <section className="surface db" aria-label="Sổ tài sản">
      <h2>Sổ tài sản</h2>
      <p className="caption wrap">Ghi chi tiết tài khoản tiền mặt ngoài tài khoản chứng khoán, sổ tiết kiệm, trái phiếu và chứng chỉ quỹ, vàng, tiền số.
        Tháp tài sản lấy mọi lớp từ đây: mỗi lớp là tổng danh sách của nó, danh sách trống là 0. Bấm Sửa để đổi một dòng rồi Lưu, Thêm để mở dòng
        mới; Xóa hỏi lại rồi xóa. Mỗi lần lưu hay xóa, Tháp tài sản tính lại. Ô lãi hay lợi suất để trống là chưa nhập, không phải 0. Sổ chưa đến
        hạn không bao giờ được tính là tiền rút ngay.</p>

      <h3>Quỹ dự phòng</h3>
      {reserveDraft === null ? <div className="db-reserve">
        <span>Quỹ dự phòng và khoản chi 12 tháng: <strong data-testid="book-reserve">{view ? formatVnd(reserve ?? view.profile_reserve) : ""}</strong>
          {view && reserve === null && <span className="caption"> (theo hồ sơ)</span>}</span>
        <span className="db-actions">
          <button type="button" className="btn" aria-label="Sửa quỹ dự phòng" disabled={locked || editing !== null}
            onClick={() => { setMessage(null); setReserveDraft(reserve === null ? "" : money(reserve)); }}><Pencil size={14} aria-hidden="true" />Sửa</button>
          {reserve !== null && <button type="button" className="btn" aria-label="Xóa quỹ dự phòng" disabled={locked || editing !== null}
            onClick={() => { if (window.confirm("Xóa số quỹ dự phòng đã nhập? Tháp tài sản sẽ dùng số theo hồ sơ.")) void saveReserve(null); }}>
            <Trash2 size={14} aria-hidden="true" />Xóa</button>}
        </span>
      </div> : <div className="db-reserve">
        <label className="field">Quỹ dự phòng và khoản chi 12 tháng (đ)<input inputMode="numeric" value={reserveDraft}
          onChange={(e) => setReserveDraft(groupDigitsInput(e.target.value))}
          placeholder={view ? `để trống = theo hồ sơ (${formatVnd(view.profile_reserve)})` : "để trống = theo hồ sơ"} /></label>
        <span className="db-actions">
          <button type="button" className="btn primary" disabled={locked} onClick={() => void saveReserve(reserveDraft)}><Check size={14} aria-hidden="true" />Lưu</button>
          <button type="button" className="btn" disabled={locked} onClick={cancel}><X size={14} aria-hidden="true" />Hủy</button>
        </span>
      </div>}
      {reserveDraft !== null && alert}
      <p className="caption wrap">Lớp dưới cùng của Tháp tài sản, và mốc để so thanh khoản bên dưới. Chưa nhập hoặc đã xóa thì lấy quỹ dự phòng và
        khoản chi trong 12 tháng ở hồ sơ đã xác nhận.</p>

      <h3>Tài khoản tiền mặt</h3>
      {table("accounts")}
      <label className="db-check"><input type="checkbox" checked={view?.book.count_ledger_cash ?? true} disabled={locked || editing !== null}
        onChange={(e) => { if (view && saved) void put(saved, e.target.checked, view.book.reserve); }} />
        Cộng thêm tiền mặt trong tài khoản chứng khoán tính từ sổ giao dịch</label>
      <p className="caption wrap">Bỏ chọn khi các tài khoản ở trên đã là toàn bộ tiền mặt của bạn (ví dụ tiền trong tài khoản chứng khoán chính là iPower):
        lớp Tiền mặt và ô Thanh khoản chỉ lấy các tài khoản này, không đếm hai lần. Lưu ngay khi đổi.</p>

      <h3>Sổ tiền gửi</h3>
      {table("deposits")}

      <h3>Trái phiếu và chứng chỉ quỹ</h3>
      <p className="caption wrap">Lợi suất là mức bạn kỳ vọng mỗi năm, dùng cho Dòng tiền thụ động; để trống thì dùng lãi suất trái phiếu ở mục đó.
        Hiệu suất năm trước không phải lợi suất bảo đảm.</p>
      {table("bonds")}
      <h3>Vàng</h3>
      {table("gold")}
      <h3>Tiền số</h3>
      {table("crypto")}
      {!editing && reserveDraft === null && alert}

      {view && view.calendar.months.length > 0 && <>
        <h3>Lịch đáo hạn</h3>
        <table className="fv-table" aria-label="Lịch đáo hạn theo tháng">
          <thead><tr><th>Tháng</th><th className="num">Số sổ</th><th className="num">Gốc về</th><th className="num">Lãi nhận khi đáo hạn</th></tr></thead>
          <tbody>{view.calendar.months.map((m) => (
            <tr key={m.month} data-testid={`maturity-${m.month}`}>
              <td data-label="Tháng">{monthLabel(m.month)}</td><td data-label="Số sổ" className="num">{m.count}</td>
              <td data-label="Gốc về" className="num">{formatVnd(m.principal)}</td>
              <td data-label="Lãi" className="num">{formatVnd(m.interest)}
                {m.missing_interest > 0 && <span className="caption"> · {m.missing_interest} sổ chưa nhập lãi</span>}</td>
            </tr>))}</tbody>
        </table>
        <p className="caption wrap">Lãi chỉ cộng cho sổ trả cuối kỳ có nhập lãi; sổ trả đầu kỳ đã nhận lãi khi mở sổ.</p>
      </>}
      {view && view.calendar.overdue.length > 0 && <p className="notice">{view.calendar.overdue.length} sổ đã qua ngày đáo hạn. Phần mềm không biết ngân hàng
        đã tái tục hay bạn đã tất toán: hãy sửa ngày đáo hạn mới hoặc xóa sổ. Gốc của sổ quá hạn vẫn ở lớp tiền gửi, không tính là rút ngay.</p>}

      {l && <>
        <h3>Thanh khoản so với quỹ dự phòng</h3>
        <dl className="eb-result" aria-label="Thanh khoản">
          <div><dt>Tiền mặt trong tài khoản chứng khoán <span className="caption">(sổ giao dịch)</span></dt>
            <dd>{l.ledger_cash_counted ? formatVnd(l.ledger_cash) : <span className="muted">không cộng ({formatVnd(l.ledger_cash)} theo sổ giao dịch)</span>}</dd></div>
          <div><dt>Tài khoản tiền mặt rút ngay</dt><dd>{formatVnd(l.accounts_liquid)}</dd></div>
          <div className="eb-main"><dt>Rút ngay được</dt><dd data-testid="liquid-now">{formatVnd(l.now)}</dd></div>
          <div><dt>Quỹ dự phòng và khoản chi 12 tháng <span className="caption">({view?.book.reserve === null ? "theo hồ sơ" : "nhập ở trên"})</span></dt><dd>{formatVnd(l.reserve)}</dd></div>
          <div><dt>So với quỹ dự phòng</dt><dd data-testid="liquid-status">{l.status === "short"
            ? <span className="negative">Thiếu {formatVnd(l.short)}</span> : <span className="positive">Đủ</span>}</dd></div>
          <div><dt>Gốc sẽ đáo hạn trong 90 ngày <span className="caption">(tham khảo)</span></dt><dd>{formatVnd(l.maturing_90d)}</dd></div>
        </dl>
        <p className="caption wrap">Chưa rút ngay, không tính ở trên: sổ phong tỏa chưa đến hạn {formatVnd(l.not_now.locked)}; sổ không phong tỏa chưa đến
          hạn {formatVnd(l.not_now.unlocked)} (rút trước hạn được, thường mất lãi); sổ quá hạn chưa cập nhật {formatVnd(l.not_now.overdue)}; tài khoản
          chưa rút được {formatVnd(l.not_now.accounts)}. Đây là phép đếm trên số bạn nhập, không phải lời khuyên rút sổ hay chuyển tiền.</p>
      </>}
    </section>
  );
}
