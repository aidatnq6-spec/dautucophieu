"use client";
import { useEffect, useState } from "react";
import { Plus, Save, Trash2 } from "lucide-react";
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

/** One list of Trái phiếu, Vàng or Tiền số: name and amount per row (bonds also an expected yield), added and removed before Lưu. */
function HoldingList({ list, rows, onChange, disabled }: { list: keyof HoldingDrafts; rows: (HoldingDraft | BondDraft)[];
  onChange: (rows: (HoldingDraft | BondDraft)[]) => void; disabled: boolean }) {
  const label = LIST_NAME[list];
  const set = (i: number, patch: Partial<BondDraft>) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <>
      {rows.length > 0 && <table className="fv-table db-table" aria-label={label}>
        <thead><tr><th>Tên</th><th>Số tiền (đ)</th>{list === "bonds" && <th>Lợi suất %/năm</th>}<th /></tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={r.id}>
            <td data-label="Tên"><input aria-label={`Tên ${label.toLowerCase()} ${i + 1}`} maxLength={80} value={r.name} onChange={(e) => set(i, { name: e.target.value })} /></td>
            <td data-label="Số tiền"><input aria-label={`Số tiền ${label.toLowerCase()} ${i + 1}`} inputMode="numeric" value={r.amount}
              onChange={(e) => set(i, { amount: groupDigitsInput(e.target.value) })} /></td>
            {list === "bonds" && <td data-label="Lợi suất"><input aria-label={`Lợi suất trái phiếu ${i + 1}`} inputMode="decimal" placeholder="chưa nhập"
              value={(r as BondDraft).rate} onChange={(e) => set(i, { rate: e.target.value })} /></td>}
            <td><button type="button" className="btn" aria-label={`Xóa ${label.toLowerCase()} ${i + 1}`} onClick={() => onChange(rows.filter((_, j) => j !== i))}>
              <Trash2 size={14} aria-hidden="true" />Xóa</button></td>
          </tr>))}</tbody>
      </table>}
      <button type="button" className="btn" disabled={disabled || rows.length >= 30}
        onClick={() => onChange([...rows, list === "bonds" ? { id: requestId(), name: "", amount: "", rate: "" } : { id: requestId(), name: "", amount: "" }])}>
        <Plus size={14} aria-hidden="true" />Thêm dòng {label.toLowerCase()}</button>
    </>
  );
}

const monthLabel = (m: string) => `${m.slice(5)}/${m.slice(0, 4)}`;

/** Sổ tài sản: cash accounts, term deposits, bonds, gold and crypto; the months deposits come back, and cash now against the reserve.
 * A sổ not yet due is never cash now; one past its date is overdue, not guessed as rolled over or closed. */
export function DepositBook({ onSaved }: { onSaved?: () => void }) {
  const [view, setView] = useState<View | null>(null);
  const [accounts, setAccounts] = useState<AccountDraft[]>([]);
  const [deposits, setDeposits] = useState<DepositDraft[]>([]);
  const [holdings, setHoldings] = useState<HoldingDrafts>(NO_HOLDINGS);
  const [countLedger, setCountLedger] = useState(true);
  const [reserve, setReserve] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  function show(v: View) {
    setView(v);
    setCountLedger(v.book.count_ledger_cash);
    setReserve(v.book.reserve === null ? "" : money(v.book.reserve));
    setAccounts(v.book.accounts.map(toAccountDraft));
    setDeposits(v.book.deposits.map(toDepositDraft));
    setHoldings(toHoldingDrafts(v.book));
  }
  useEffect(() => { api<View>("deposit-book").then(show, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function save() {
    if (!view) return;
    const r = bookPayload(accounts, deposits, holdings);
    if ("error" in r) { setMessage(r.error); return; }
    const res = reservePayload(reserve);
    if ("error" in res) { setMessage(res.error); return; }
    try {
      show(await api<View>("deposit-book", { method: "PUT", body: { ...r.ok, count_ledger_cash: countLedger, reserve: res.ok, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      onSaved?.();
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const setAccount = (i: number, patch: Partial<AccountDraft>) => setAccounts(accounts.map((a, j) => (j === i ? { ...a, ...patch } : a)));
  const setDeposit = (i: number, patch: Partial<DepositDraft>) => setDeposits(deposits.map((d, j) => (j === i ? { ...d, ...patch } : d)));
  const status = (id: string) => view?.calendar.overdue.includes(id) ? <span className="pill bad">quá hạn, cần cập nhật</span>
    : view?.calendar.due_soon.includes(id) ? <span className="pill warn">sắp đến hạn</span> : null;
  const l = view?.liquidity;
  return (
    <section className="surface db" aria-label="Sổ tài sản">
      <h2>Sổ tài sản</h2>
      <p className="caption wrap">Ghi chi tiết tài khoản tiền mặt ngoài tài khoản chứng khoán, sổ tiết kiệm, trái phiếu và chứng chỉ quỹ, vàng, tiền số.
        Đã lưu sổ thì Tháp tài sản lấy mọi lớp từ đây: mỗi lớp là tổng danh sách của nó, danh sách trống là 0; các số nhập tay trước đó không còn được
        tính. Tài khoản tiền mặt cộng vào lớp Tiền mặt. Ô lãi hay lợi suất để trống là chưa nhập, không phải 0. Sổ chưa đến hạn không bao giờ được
        tính là tiền rút ngay.</p>

      <h3>Quỹ dự phòng</h3>
      <label className="field">Quỹ dự phòng và khoản chi 12 tháng (đ)<input inputMode="numeric" value={reserve} disabled={!view}
        onChange={(e) => setReserve(groupDigitsInput(e.target.value))}
        placeholder={view ? `để trống = theo hồ sơ (${formatVnd(view.profile_reserve)})` : "để trống = theo hồ sơ"} /></label>
      <p className="caption wrap">Lớp dưới cùng của Tháp tài sản, và mốc để so thanh khoản bên dưới. Để trống thì lấy quỹ dự phòng và khoản chi
        trong 12 tháng ở hồ sơ đã xác nhận.</p>

      <h3>Tài khoản tiền mặt</h3>
      {accounts.length > 0 && <table className="fv-table db-table" aria-label="Tài khoản tiền mặt">
        <thead><tr><th>Tên</th><th>Số tiền (đ)</th><th>Rút ngay</th><th /></tr></thead>
        <tbody>{accounts.map((a, i) => (
          <tr key={a.id}>
            <td data-label="Tên"><input aria-label={`Tên tài khoản ${i + 1}`} maxLength={60} value={a.name} onChange={(e) => setAccount(i, { name: e.target.value })} /></td>
            <td data-label="Số tiền"><input aria-label={`Số tiền tài khoản ${i + 1}`} inputMode="numeric" value={a.amount}
              onChange={(e) => setAccount(i, { amount: groupDigitsInput(e.target.value) })} /></td>
            <td data-label="Rút ngay"><input type="checkbox" aria-label={`Tài khoản ${i + 1} rút ngay được`} checked={a.liquid}
              onChange={(e) => setAccount(i, { liquid: e.target.checked })} /></td>
            <td><button type="button" className="btn" aria-label={`Xóa tài khoản ${i + 1}`} onClick={() => setAccounts(accounts.filter((_, j) => j !== i))}>
              <Trash2 size={14} aria-hidden="true" />Xóa</button></td>
          </tr>))}</tbody>
      </table>}
      <label className="db-check"><input type="checkbox" checked={countLedger} disabled={!view} onChange={(e) => setCountLedger(e.target.checked)} />
        Cộng thêm tiền mặt trong tài khoản chứng khoán tính từ sổ giao dịch</label>
      <p className="caption wrap">Bỏ chọn khi các tài khoản ở trên đã là toàn bộ tiền mặt của bạn (ví dụ tiền trong tài khoản chứng khoán chính là iPower):
        lớp Tiền mặt và ô Thanh khoản chỉ lấy các tài khoản này, không đếm hai lần. Lưu để áp dụng.</p>
      <button type="button" className="btn" disabled={!view || accounts.length >= 30}
        onClick={() => setAccounts([...accounts, { id: requestId(), name: "", amount: "", liquid: true }])}><Plus size={14} aria-hidden="true" />Thêm tài khoản</button>

      <h3>Sổ tiền gửi</h3>
      {deposits.length > 0 && <table className="fv-table db-table" aria-label="Sổ tiền gửi">
        <thead><tr><th>Ngân hàng</th><th>Đáo hạn</th><th>Gốc (đ)</th><th>Lãi suất %/năm</th><th>Lãi dự kiến (đ)</th><th>Trả lãi</th><th>Phong tỏa</th><th /></tr></thead>
        <tbody>{deposits.map((d, i) => (
          <tr key={d.id}>
            <td data-label="Ngân hàng"><input aria-label={`Ngân hàng sổ ${i + 1}`} maxLength={40} value={d.bank} onChange={(e) => setDeposit(i, { bank: e.target.value })} /></td>
            <td data-label="Đáo hạn"><input type="date" aria-label={`Ngày đáo hạn sổ ${i + 1}`} value={d.matures} onChange={(e) => setDeposit(i, { matures: e.target.value })} />
              {status(d.id)}</td>
            <td data-label="Gốc"><input aria-label={`Tiền gốc sổ ${i + 1}`} inputMode="numeric" value={d.principal}
              onChange={(e) => setDeposit(i, { principal: groupDigitsInput(e.target.value) })} /></td>
            <td data-label="Lãi suất"><input aria-label={`Lãi suất sổ ${i + 1}`} inputMode="decimal" placeholder="chưa nhập" value={d.rate}
              onChange={(e) => setDeposit(i, { rate: e.target.value })} /></td>
            <td data-label="Lãi dự kiến"><input aria-label={`Lãi dự kiến sổ ${i + 1}`} inputMode="numeric" placeholder="chưa nhập" value={d.interest}
              onChange={(e) => setDeposit(i, { interest: groupDigitsInput(e.target.value) })} /></td>
            <td data-label="Trả lãi"><select aria-label={`Cách trả lãi sổ ${i + 1}`} value={d.payout} onChange={(e) => setDeposit(i, { payout: e.target.value as "end" | "upfront" })}>
              <option value="end">Cuối kỳ</option><option value="upfront">Đầu kỳ (đã nhận)</option></select></td>
            <td data-label="Phong tỏa"><input type="checkbox" aria-label={`Sổ ${i + 1} phong tỏa đến hạn`} checked={d.locked}
              onChange={(e) => setDeposit(i, { locked: e.target.checked })} /></td>
            <td><button type="button" className="btn" aria-label={`Xóa sổ ${i + 1}`} onClick={() => setDeposits(deposits.filter((_, j) => j !== i))}>
              <Trash2 size={14} aria-hidden="true" />Xóa</button></td>
          </tr>))}</tbody>
      </table>}
      <button type="button" className="btn" disabled={!view || deposits.length >= 100}
        onClick={() => setDeposits([...deposits, { id: requestId(), bank: "", matures: "", principal: "", rate: "", interest: "", payout: "end", locked: true }])}>
        <Plus size={14} aria-hidden="true" />Thêm sổ</button>

      <h3>Trái phiếu và chứng chỉ quỹ</h3>
      <p className="caption wrap">Lợi suất là mức bạn kỳ vọng mỗi năm, dùng cho Dòng tiền thụ động; để trống thì dùng lãi suất trái phiếu ở mục đó.
        Hiệu suất năm trước không phải lợi suất bảo đảm.</p>
      <HoldingList list="bonds" rows={holdings.bonds} disabled={!view} onChange={(rows) => setHoldings({ ...holdings, bonds: rows as BondDraft[] })} />
      <h3>Vàng</h3>
      <HoldingList list="gold" rows={holdings.gold} disabled={!view} onChange={(rows) => setHoldings({ ...holdings, gold: rows })} />
      <h3>Tiền số</h3>
      <HoldingList list="crypto" rows={holdings.crypto} disabled={!view} onChange={(rows) => setHoldings({ ...holdings, crypto: rows })} />

      <div className="actions">
        <button type="button" className="btn primary" disabled={!view} onClick={() => void save()}><Save size={16} aria-hidden="true" />Lưu sổ tài sản</button>
      </div>
      {message && <p className="errors" role="alert">{message}</p>}

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
