"use client";
import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";
import type { Method } from "./loan-calc";
import { rentalCompare, type Rental } from "./rental-calc";

const EMPTY = { price: "", own: "", upfront: "", rent: "", running: "", loanRate: "", termYears: "", depositRate: "", years: "" };
type Key = keyof typeof EMPTY;
const MONEY: [Key, string][] = [["price", "Giá nhà (đ)"], ["own", "Vốn tự có (đ)"], ["upfront", "Chi phí mua ban đầu (đ)"], ["rent", "Tiền thuê mỗi tháng (đ)"], ["running", "Chi phí giữ nhà mỗi tháng (đ)"]];
const vnd = (v: number) => formatVnd(String(Math.round(v)));
const pct = (v: number) => formatRatio(v.toFixed(6), 2);
const read = (s: string) => { const p = s.trim() ? parseMoneyInput(s) : null; return p === null ? null : Number(p); };

/** Buy a home to let, or keep the money on deposit: the yield, the monthly cash and the growth in price needed to match the deposit. Runs in the browser; nothing is saved. */
export function RentalCompare() {
  const [f, setF] = useState(EMPTY);
  const [method, setMethod] = useState<Method>("declining");
  const [prefilled, setPrefilled] = useState(false);
  const set = (k: Key, v: string) => setF((old) => ({ ...old, [k]: v }));
  useEffect(() => {
    api<{ default_rate: string | null }>("passive-income").then((v) => {
      if (!v.default_rate) return;
      setF((old) => (old.depositRate ? old : { ...old, depositRate: v.default_rate!.replace(".", ",") }));
      setPrefilled(true);
    }, () => undefined);  // no rate to offer: the box stays empty for the owner to fill
  }, []);
  const out = useMemo<{ error: string } | { result: Rental } | null>(() => {
    const [price, own, upfront, rent, running, depositRate, years] = (["price", "own", "upfront", "rent", "running", "depositRate", "years"] as Key[]).map((k) => read(f[k]));
    if (price === null || own === null || upfront === null || rent === null || running === null || depositRate === null || years === null) return null;
    if (price <= 0) return { error: "Giá nhà phải lớn hơn 0." };
    if (own > price + upfront) return { error: "Vốn tự có không được lớn hơn giá nhà cộng chi phí mua." };
    if (depositRate > 100) return { error: "Lãi tiền gửi từ 0 đến 100%." };
    if (!Number.isInteger(years) || years < 1 || years > 50) return { error: "Số năm nắm giữ là số nguyên từ 1 đến 50." };
    const borrowing = price + upfront > own, loanRate = read(f.loanRate), termYears = read(f.termYears);
    if (borrowing && (loanRate === null || termYears === null)) return null;
    if (borrowing && (loanRate! > 100 || !Number.isInteger(termYears!) || termYears! < 1 || termYears! > 50)) return { error: "Lãi vay từ 0 đến 100%, thời hạn vay là số nguyên từ 1 đến 50 năm." };
    return { result: rentalCompare({ price, own, upfront, rent, running, depositRate, years, loanRate: loanRate ?? 0, termYears: termYears ?? 1, method }) };
  }, [f, method]);
  const r = out && "result" in out ? out.result : null;
  return (
    <section className="surface rc" aria-label="Mua nhà cho thuê hay giữ tiền gửi">
      <h2>Mua nhà cho thuê hay giữ tiền gửi</h2>
      <p className="caption">So sánh khi có cơ hội: cùng số vốn, sau cùng số năm, nhà phải tăng giá bao nhiêu thì mới bằng giữ tiền gửi. Tính ngay trên trình duyệt, không lưu và không gửi đi đâu.</p>
      <div className="eb-form">
        {MONEY.map(([k, label]) => <label key={k} className="field">{label}<input inputMode="numeric" value={f[k]} onChange={(e) => set(k, groupDigitsInput(e.target.value))} /></label>)}
        <label className="field">Lãi vay (%/năm)<input inputMode="decimal" value={f.loanRate} onChange={(e) => set("loanRate", e.target.value)} /></label>
        <label className="field">Thời hạn vay (năm)<input inputMode="numeric" value={f.termYears} onChange={(e) => set("termYears", e.target.value)} /></label>
        <label className="field">Cách trả<select aria-label="Cách trả khoản vay mua nhà" value={method} onChange={(e) => setMethod(e.target.value as Method)}><option value="declining">Dư nợ giảm dần</option><option value="annuity">Trả đều hàng tháng</option></select></label>
        <label className="field">Lãi tiền gửi (%/năm)<input inputMode="decimal" value={f.depositRate} onChange={(e) => { set("depositRate", e.target.value); setPrefilled(false); }} /></label>
        <label className="field">Số năm nắm giữ<input inputMode="numeric" value={f.years} onChange={(e) => set("years", e.target.value)} /></label>
      </div>
      {prefilled && <p className="caption">Lãi tiền gửi đang lấy mức 12 tháng ở trang Vĩ mô; bạn có thể sửa.</p>}
      {out === null && <p className="muted" data-testid="rc-empty">Nhập đủ các ô để tính. Ô nào bằng 0 thì nhập 0; lãi vay và thời hạn chỉ cần khi có vay.</p>}
      {out && "error" in out && <p className="errors" role="alert">{out.error}</p>}
      {r && <>
        <p className="rc-verdict" data-testid="rc-growth">{r.neededGrowth === null
          ? `Chỉ riêng dòng tiền cho thuê sau ${read(f.years)} năm đã hơn giữ tiền gửi, không cần nhà tăng giá.`
          : <>Để bằng giữ tiền gửi sau {read(f.years)} năm, giá nhà cần {r.neededGrowth >= 0 ? "tăng" : "giảm không quá"} khoảng <strong>{pct(Math.abs(r.neededGrowth))}/năm</strong>, tức bán được ít nhất {vnd(r.neededPrice)}.</>}</p>
        <dl className="ln-flow">
          <div><dt>Lợi suất cho thuê trước chi phí</dt><dd data-testid="rc-gross">{pct(r.grossYield)}</dd></div>
          <div><dt>Lợi suất cho thuê sau chi phí</dt><dd data-testid="rc-net">{pct(r.netYield)}</dd></div>
          <div><dt>Số tiền vay</dt><dd>{vnd(r.loan)}</dd></div>
          <div><dt>Dòng tiền tháng đầu (thuê trừ chi phí và trả nợ)</dt><dd className={r.firstFlow < 0 ? "negative" : undefined}>{vnd(r.firstFlow)}</dd></div>
          <div><dt>Vốn tự có nếu giữ tiền gửi đến cuối kỳ</dt><dd>{vnd(r.keep)}</dd></div>
          <div><dt>Dư nợ còn lại cuối kỳ</dt><dd>{vnd(r.balance)}</dd></div>
        </dl>
      </>}
      <p className="caption">Tiền thuê, chi phí và lãi suất giữ nguyên suốt thời gian; tháng nào thiếu thì coi như bù từ tiền gửi, dư thì gửi thêm. Chưa tính thuế, phí khi bán và tháng không có khách. Phần mềm không dự báo giá nhà. Không phải khuyến nghị.</p>
    </section>
  );
}
