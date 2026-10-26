"use client";
import { useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api, requestId, type ApiFailure } from "../lib/api";
import { parseMoneyInput, hanoiDate } from "../lib/format";
import { FormErrors } from "./form-errors";

export type LedgerEvent = { event_id: string; type: string; effective_at: string; sequence: number; security_id?: string; quantity?: number;
  price?: string; fee?: string; tax?: string; amount?: string; settlement_date?: string | null; note?: string; [k: string]: unknown };

const TYPES: [string, string][] = [["deposit", "Nộp tiền"], ["withdrawal", "Rút tiền"], ["buy", "Mua"], ["sell", "Bán"],
  ["opening_balance", "Số dư đầu kỳ"], ["cash_dividend_entitlement", "Quyền cổ tức tiền"], ["cash_dividend_payment", "Nhận cổ tức tiền"]];
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
  const [actionId, setActionId] = useState(String(editing?.action_id ?? ""));
  const [recordDate, setRecordDate] = useState(String(editing?.record_date ?? ""));
  const [paymentDate, setPaymentDate] = useState(String(editing?.payment_date ?? ""));
  const [eligibleQuantity, setEligibleQuantity] = useState(String(editing?.eligible_quantity ?? ""));
  const [expectedGross, setExpectedGross] = useState(String(editing?.expected_gross ?? ""));
  const [expectedTax, setExpectedTax] = useState(String(editing?.expected_tax ?? "0"));
  const [receivedNet, setReceivedNet] = useState(String(editing?.received_net ?? ""));
  const [taxWithheld, setTaxWithheld] = useState(String(editing?.tax_withheld ?? "0"));
  const [openingPositions, setOpeningPositions] = useState(() => Array.isArray(editing?.positions)
    ? (editing.positions as { security_id: string; quantity: number; total_cost: string }[]).map((p) => `${p.security_id},${p.quantity},${p.total_cost}`).join("\n") : "");
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
    } else if (type === "opening_balance") {
      const positions = openingPositions.split(/\r?\n/).filter((line) => line.trim()).map((line, i) => {
        const [security, rawQuantity, rawCost, ...extra] = line.split(",").map((part) => part.trim());
        const q = Number(rawQuantity);
        const cost = parseMoneyInput(rawCost ?? "");
        if (extra.length || !/^[A-Z0-9]{3,10}$/.test((security ?? "").toUpperCase()) || !Number.isInteger(q) || q <= 0 || cost === null) {
          problems.push(`Vị thế đầu kỳ dòng ${i + 1} phải có dạng MÃ,SỐ_LƯỢNG,TỔNG_GIÁ_VỐN`);
        }
        return { security_id: (security ?? "").toUpperCase(), quantity: q, total_cost: cost ?? "0" };
      });
      Object.assign(base, { cash: money("Tiền mặt đầu kỳ", amount), positions });
    } else if (type === "cash_dividend_entitlement") {
      const q = Number(eligibleQuantity);
      if (!actionId.trim()) problems.push("Cần mã sự kiện cổ tức");
      if (!recordDate) problems.push("Cần ngày chốt quyền");
      if (!Number.isInteger(q) || q <= 0) problems.push("Số cổ phiếu hưởng quyền phải là số nguyên dương");
      if (!/^[A-Z0-9]{3,10}$/.test(ticker.trim().toUpperCase())) problems.push("Mã cổ phiếu không hợp lệ");
      Object.assign(base, { action_id: actionId.trim(), security_id: ticker.trim().toUpperCase(), record_date: recordDate,
        payment_date: paymentDate || null, eligible_quantity: q, expected_gross: money("Cổ tức gộp dự kiến", expectedGross),
        expected_tax: money("Thuế dự kiến", expectedTax) });
    } else if (type === "cash_dividend_payment") {
      if (!actionId.trim()) problems.push("Cần mã sự kiện cổ tức đã ghi nhận quyền");
      Object.assign(base, { action_id: actionId.trim(), received_net: money("Tiền thực nhận", receivedNet), tax_withheld: money("Thuế đã khấu trừ", taxWithheld) });
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
        </>) : type === "opening_balance" ? (<>
          <label className="field">Tiền mặt đầu kỳ (đ)<input inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} /></label>
          <label className="field">Vị thế đầu kỳ<textarea value={openingPositions} onChange={(e) => setOpeningPositions(e.target.value)}
            placeholder={"FPT,100,10000000\nVCB,200,18000000"} /></label>
        </>) : type === "cash_dividend_entitlement" ? (<>
          <label className="field">Mã sự kiện<input value={actionId} onChange={(e) => setActionId(e.target.value)} placeholder="div-FPT-2026" /></label>
          <label className="field">Mã cổ phiếu<input value={ticker} onChange={(e) => setTicker(e.target.value)} /></label>
          <label className="field">Ngày chốt quyền<input type="date" value={recordDate} onChange={(e) => setRecordDate(e.target.value)} /></label>
          <label className="field">Ngày thanh toán dự kiến<input type="date" value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} /></label>
          <label className="field">Số cổ phiếu hưởng quyền<input inputMode="numeric" value={eligibleQuantity} onChange={(e) => setEligibleQuantity(e.target.value)} /></label>
          <label className="field">Cổ tức gộp dự kiến (đ)<input inputMode="numeric" value={expectedGross} onChange={(e) => setExpectedGross(e.target.value)} /></label>
          <label className="field">Thuế dự kiến (đ)<input inputMode="numeric" value={expectedTax} onChange={(e) => setExpectedTax(e.target.value)} /></label>
        </>) : type === "cash_dividend_payment" ? (<>
          <label className="field">Mã sự kiện quyền đã ghi<input value={actionId} onChange={(e) => setActionId(e.target.value)} /></label>
          <label className="field">Tiền thực nhận (đ)<input inputMode="numeric" value={receivedNet} onChange={(e) => setReceivedNet(e.target.value)} /></label>
          <label className="field">Thuế đã khấu trừ (đ)<input inputMode="numeric" value={taxWithheld} onChange={(e) => setTaxWithheld(e.target.value)} /></label>
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
