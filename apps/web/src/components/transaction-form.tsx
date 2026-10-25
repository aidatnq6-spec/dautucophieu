"use client";
import { useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api, requestId, type ApiFailure } from "../lib/api";
import { parseMoneyInput, hanoiDate } from "../lib/format";
import { FormErrors } from "./form-errors";

export type LedgerEvent = { event_id: string; type: string; effective_at: string; sequence: number; security_id?: string; quantity?: number;
  price?: string; fee?: string; tax?: string; amount?: string; settlement_date?: string | null; note?: string; [k: string]: unknown };

const TYPES: [string, string][] = [["deposit", "Nộp tiền"], ["withdrawal", "Rút tiền"], ["buy", "Mua"], ["sell", "Bán"]];
export const TYPE_LABEL: Record<string, string> = Object.fromEntries([...TYPES, ["opening_balance", "Số dư đầu kỳ"],
  ["cash_dividend_entitlement", "Quyền cổ tức tiền"], ["cash_dividend_payment", "Nhận cổ tức tiền"], ["stock_dividend_entitlement", "Quyền cổ phiếu thưởng"],
  ["stock_dividend_credit", "Cổ phiếu thưởng về"], ["share_split", "Tách/gộp"], ["unsupported_action", "Sự kiện chưa hỗ trợ"]]);
export const LEDGER_ERRORS: Record<string, string> = {
  ledger_oversell: "Số lượng bán vượt số cổ phiếu đang có.", ledger_cash_negative: "Tiền trong sổ sẽ âm: cần ghi nộp tiền trước.",
  ledger_ambiguous_order: "Đã có giao dịch cùng ngày và cùng thứ tự: đổi thứ tự trong ngày.", ledger_duplicate_event: "Mã giao dịch đã tồn tại.",
  version_conflict: "Sổ đã thay đổi ở nơi khác: tải lại trang rồi nhập lại.",
};

export function TransactionForm({ ledgerVersion, events, editing, onSaved, onCancel }:
  { ledgerVersion: number; events: LedgerEvent[]; editing: LedgerEvent | null; onSaved: () => void; onCancel?: () => void }) {
  const today = hanoiDate();
  const [type, setType] = useState(editing?.type ?? "deposit");
  const [day, setDay] = useState(editing?.effective_at ?? today);
  const [sequence, setSequence] = useState(String(editing?.sequence ?? events.filter((e) => e.effective_at === today).length));
  const [ticker, setTicker] = useState(editing?.security_id ?? "");
  const [quantity, setQuantity] = useState(editing?.quantity ? String(editing.quantity) : "");
  const [price, setPrice] = useState(editing?.price ?? "");
  const [fee, setFee] = useState(editing?.fee ?? "0");
  const [tax, setTax] = useState(editing?.tax ?? "0");
  const [amount, setAmount] = useState(editing?.amount ?? "");
  const [settlement, setSettlement] = useState(editing?.settlement_date ?? "");
  const [reason, setReason] = useState("");
  const [failure, setFailure] = useState<ApiFailure | null>(null);
  const [local, setLocal] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const trade = type === "buy" || type === "sell";

  function event(): LedgerEvent | null {
    const problems: string[] = [];
    const money = (label: string, raw: string) => { const v = parseMoneyInput(raw); if (v === null) problems.push(`${label} không hợp lệ`); return v ?? "0"; };
    const seq = Number(sequence);
    if (!Number.isInteger(seq) || seq < 0) problems.push("Thứ tự trong ngày phải là số nguyên không âm");
    const base: LedgerEvent = { event_id: editing?.event_id ?? `ev-${requestId().slice(0, 20)}`, type, effective_at: day, sequence: seq,
      settlement_date: settlement || null };
    if (trade) {
      const q = Number(quantity);
      if (!/^[1-9]\d*$/.test(quantity)) problems.push("Số lượng phải là số nguyên dương");
      if (!/^[A-Z0-9]{3,10}$/.test(ticker.trim().toUpperCase())) problems.push("Mã cổ phiếu không hợp lệ");
      Object.assign(base, { security_id: ticker.trim().toUpperCase(), quantity: q, price: money("Giá", price), fee: money("Phí", fee), tax: money("Thuế", tax) });
    } else {
      Object.assign(base, { amount: money("Số tiền", amount) });
    }
    if (editing && !reason.trim()) problems.push("Cần ghi lý do sửa");
    setLocal(problems);
    return problems.length ? null : base;
  }

  async function submit() {
    const ev = event();
    setFailure(null);
    if (!ev) return;
    setBusy(true);
    try {
      if (editing) {
        await api("ledger/amendments", { method: "POST", body: { amendment: { amendment_id: `am-${requestId().slice(0, 20)}`, action: "replace",
          target_event_id: editing.event_id, replacement: ev, reason: reason.trim() }, expected_version: ledgerVersion, request_id: requestId() } });
      } else {
        await api("ledger/events", { method: "POST", body: { event: ev, expected_version: ledgerVersion, request_id: requestId() } });
      }
      onSaved();
    } catch (e) {
      if (e instanceof ApiError) setFailure({ ...e.failure, message: LEDGER_ERRORS[e.failure.code] ?? e.failure.message });
    } finally { setBusy(false); }
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); void submit(); }} aria-label={editing ? "Sửa giao dịch" : "Ghi nhận giao dịch"}>
      <FormErrors failure={failure} local={local} />
      <div className="formgrid">
        <label className="field">Loại giao dịch<select value={type} onChange={(e) => setType(e.target.value)} disabled={!!editing}>
          {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label className="field">Ngày giao dịch<input type="date" value={day} onChange={(e) => setDay(e.target.value)} required /></label>
        <label className="field">Thứ tự trong ngày<input inputMode="numeric" value={sequence} onChange={(e) => setSequence(e.target.value)} /></label>
        {trade ? (<>
          <label className="field">Mã cổ phiếu<input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="FPT" autoCapitalize="characters" /></label>
          <label className="field">Số lượng<input inputMode="numeric" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></label>
          <label className="field">Giá thực hiện (đ/cp)<input inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value)} /></label>
          <label className="field">Phí thực tế (đ)<input inputMode="numeric" value={fee} onChange={(e) => setFee(e.target.value)} /></label>
          <label className="field">Thuế thực tế (đ)<input inputMode="numeric" value={tax} onChange={(e) => setTax(e.target.value)} /></label>
          <label className="field">Ngày thanh toán (theo sao kê)<input type="date" value={settlement} onChange={(e) => setSettlement(e.target.value)} /></label>
        </>) : (
          <label className="field">Số tiền (đ)<input inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} /></label>
        )}
        {editing && <label className="field">Lý do sửa<input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Sửa theo sao kê" /></label>}
      </div>
      <p className="caption">Phí và thuế nhập theo chứng từ; ứng dụng không tự áp tỷ lệ. Chưa bấm lưu thì chưa ghi vào sổ.</p>
      <div className="actions">
        <button type="submit" className="btn primary" disabled={busy}><Save size={16} aria-hidden="true" />{editing ? "Lưu bản sửa" : "Ghi vào sổ"}</button>
        {onCancel && <button type="button" className="btn" onClick={onCancel}>Hủy bỏ</button>}
      </div>
    </form>
  );
}
