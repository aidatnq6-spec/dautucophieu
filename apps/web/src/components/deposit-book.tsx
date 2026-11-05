"use client";
import { useEffect, useState } from "react";
import { Plus, Save, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";

type Account = { id: string; name: string; amount: string; liquid: boolean };
type Deposit = { id: string; bank: string; matures: string; principal: string; rate: string | null; interest: string | null;
  payout: "end" | "upfront"; locked: boolean };
type Month = { month: string; count: number; principal: string; interest: string; missing_interest: number };
type Liquidity = { now: string; ledger_cash: string; accounts_liquid: string; reserve: string; status: "enough" | "short"; short: string | null;
  maturing_90d: string; not_now: { accounts: string; locked: string; unlocked: string; overdue: string } };
type View = { version: number; book: { accounts: Account[]; deposits: Deposit[] };
  calendar: { months: Month[]; due_soon: string[]; overdue: string[] }; liquidity: Liquidity };

/** Rows as typed: money grouped with dots, rate with a comma, blanks kept blank. */
export type AccountDraft = Account;
export type DepositDraft = Omit<Deposit, "rate" | "interest"> & { rate: string; interest: string };

const money = (v: string) => formatVnd(v, { unit: false });
const toAccountDraft = (a: Account): AccountDraft => ({ ...a, amount: money(a.amount) });
const toDepositDraft = (d: Deposit): DepositDraft => ({ ...d, principal: money(d.principal), interest: d.interest === null ? "" : money(d.interest),
  rate: d.rate === null ? "" : d.rate.replace(".", ",") });
const whole = (raw: string) => { const v = parseMoneyInput(raw); return v !== null && !v.includes(".") ? v : null; };

/** The book the API takes, or the first row that cannot be saved, named by its place in the table. Blank rate or interest = unknown (null). */
export function bookPayload(accounts: AccountDraft[], deposits: DepositDraft[]): { ok: { accounts: Account[]; deposits: Deposit[] } } | { error: string } {
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
  return { ok: { accounts: outAccounts, deposits: outDeposits } };
}

const monthLabel = (m: string) => `${m.slice(5)}/${m.slice(0, 4)}`;

/** Sổ tiền gửi và tiền mặt: cash accounts and term deposits, the months their money comes back, and cash now against the reserve.
 * A sổ not yet due is never cash now; one past its date is overdue, not guessed as rolled over or closed. */
export function DepositBook({ onSaved }: { onSaved?: () => void }) {
  const [view, setView] = useState<View | null>(null);
  const [accounts, setAccounts] = useState<AccountDraft[]>([]);
  const [deposits, setDeposits] = useState<DepositDraft[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  function show(v: View) {
    setView(v);
    setAccounts(v.book.accounts.map(toAccountDraft));
    setDeposits(v.book.deposits.map(toDepositDraft));
  }
  useEffect(() => { api<View>("deposit-book").then(show, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function save() {
    if (!view) return;
    const r = bookPayload(accounts, deposits);
    if ("error" in r) { setMessage(r.error); return; }
    try {
      show(await api<View>("deposit-book", { method: "PUT", body: { ...r.ok, expected_version: view.version, request_id: requestId() } }));
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
    <section className="surface db" aria-label="Sổ tiền gửi và tiền mặt">
      <h2>Sổ tiền gửi và tiền mặt</h2>
      <p className="caption wrap">Ghi từng sổ tiết kiệm và tài khoản tiền mặt ngoài tài khoản chứng khoán. Có ít nhất một sổ thì lớp Tiền gửi của Tháp tài
        sản lấy tổng gốc các sổ; tài khoản tiền mặt cộng vào lớp Tiền mặt. Ô lãi để trống là chưa nhập, không phải 0. Sổ chưa đến hạn không bao giờ
        được tính là tiền rút ngay.</p>

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
      <div className="actions">
        <button type="button" className="btn" disabled={!view || deposits.length >= 100}
          onClick={() => setDeposits([...deposits, { id: requestId(), bank: "", matures: "", principal: "", rate: "", interest: "", payout: "end", locked: true }])}>
          <Plus size={14} aria-hidden="true" />Thêm sổ</button>
        <button type="button" className="btn primary" disabled={!view} onClick={() => void save()}><Save size={16} aria-hidden="true" />Lưu sổ tiền gửi</button>
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
          <div><dt>Tiền mặt trong tài khoản chứng khoán <span className="caption">(sổ giao dịch)</span></dt><dd>{formatVnd(l.ledger_cash)}</dd></div>
          <div><dt>Tài khoản tiền mặt rút ngay</dt><dd>{formatVnd(l.accounts_liquid)}</dd></div>
          <div className="eb-main"><dt>Rút ngay được</dt><dd data-testid="liquid-now">{formatVnd(l.now)}</dd></div>
          <div><dt>Quỹ dự phòng và khoản chi 12 tháng <span className="caption">(như Tháp tài sản)</span></dt><dd>{formatVnd(l.reserve)}</dd></div>
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
