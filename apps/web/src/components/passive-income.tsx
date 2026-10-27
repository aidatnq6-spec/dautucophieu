"use client";
import { useEffect, useState } from "react";
import { Target } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";

type Result = { required: string; income_now: string | null; progress: string | null; months: number | null; reached_on: string | null; rate: string };
type Income = { deposit: string; bond: string; dividends: string; stocks?: string; total: string };
type View = { version: number; goal: { target: string; rate: string | null; bond_rate: string; stock_rate?: string | null } | null; default_rate: string | null; default_bond_rate: string;
  income: Income | null; result: Result | null; capital: string | null; contribution: string };

const rate = (v: string) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 2 });

function when(r: Result) {
  if (r.months === null) return "Chưa đạt trong 50 năm với giả định hiện tại";
  if (r.months === 0) return "Đã đạt";
  const years = Math.floor(r.months / 12), months = r.months % 12;
  const span = years ? `khoảng ${years} năm${months ? ` ${months} tháng` : ""}` : `khoảng ${months} tháng`;
  return `${span} (khoảng ${r.reached_on!.slice(5, 7)}/${r.reached_on!.slice(0, 4)})`;
}

/** Capital needed for a monthly income at an assumed rate, the income today's capital would pay, and time to the goal. An estimate. */
export function PassiveIncome() {
  const [view, setView] = useState<View | null>(null);
  const [target, setTarget] = useState("");
  const [yieldRate, setYieldRate] = useState("");
  const [bondRate, setBondRate] = useState("");
  const [stockRate, setStockRate] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>("passive-income").then((v) => {
      setView(v);
      if (v.goal) { setTarget(formatVnd(v.goal.target, { unit: false })); if (v.goal.rate) setYieldRate(v.goal.rate.replace(".", ",")); }
      setBondRate((v.goal?.bond_rate ?? v.default_bond_rate).replace(".", ","));
      if (v.goal?.stock_rate) setStockRate(v.goal.stock_rate.replace(".", ","));
    }, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  async function save() {
    if (!view) return;
    const t = parseMoneyInput(target);
    const r = yieldRate.trim() ? parseMoneyInput(yieldRate) : null;  // empty = the 12-month deposit rate
    const b = bondRate.trim() ? parseMoneyInput(bondRate) : null;
    const s = stockRate.trim() ? parseMoneyInput(stockRate) : null;  // empty = last year's cash dividends
    if (t === null || t.includes(".") || (yieldRate.trim() && r === null)) { setMessage("Nhập dòng tiền mong muốn (đồng) và tỷ suất (%), hoặc để trống tỷ suất."); return; }
    try {
      setView(await api<View>("passive-income", { method: "PUT", body: { target: t, rate: r, bond_rate: b, stock_rate: s, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const r = view?.result;
  return (
    <section className="surface" aria-label="Mục tiêu dòng tiền thụ động">
      <h2>Mục tiêu dòng tiền thụ động</h2>
      <p className="caption">Cần bao nhiêu vốn để tài sản tạo ra dòng tiền mỗi tháng như mong muốn, và với vốn hiện có (Tháp tài sản, trừ quỹ dự phòng) cộng
        góp đều mỗi tháng (Góp vốn đều), tái đầu tư ở cùng tỷ suất, thì khoảng bao lâu đạt. Dòng tiền hiện tại tính theo tài sản thực trả (tiền gửi, trái phiếu, cổ tức); vốn cần có và thời gian đạt dùng tỷ suất giả định. Ước tính đơn giản, theo tiền hôm nay, chưa tính lạm phát;
        không phải khuyến nghị.</p>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <label className="field">Dòng tiền mong muốn mỗi tháng (đ)<input inputMode="numeric" value={target} disabled={!view} onChange={(e) => setTarget(groupDigitsInput(e.target.value))} /></label>
        <label className="field">Tỷ suất dòng tiền giả định (%/năm)<input inputMode="decimal" value={yieldRate} disabled={!view} onChange={(e) => setYieldRate(e.target.value)}
          placeholder={view?.default_rate ? `để trống = lãi tiền gửi 12 tháng (${rate(view.default_rate)}%)` : "ví dụ 6"} /></label>
        <label className="field">Lãi suất trái phiếu (%/năm)<input inputMode="decimal" value={bondRate} disabled={!view} onChange={(e) => setBondRate(e.target.value)} /></label>
        <label className="field">Lợi suất cổ phiếu (%/năm)<input inputMode="decimal" value={stockRate} disabled={!view} onChange={(e) => setStockRate(e.target.value)}
          placeholder="để trống = cổ tức tiền mặt 12 tháng" /></label>
        <button type="submit" className="btn primary" disabled={!view}><Target size={16} aria-hidden="true" />Tính mục tiêu</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {view?.goal && !r && <p className="notice">Chưa có lãi tiền gửi 12 tháng ở trang Vĩ mô; nhập tỷ suất giả định để tính.</p>}
      {r && <dl className="eb-result">
        <div><dt>Vốn cần có (tỷ suất {rate(r.rate)}%/năm)</dt><dd data-testid="pi-required">{formatVnd(r.required)}</dd></div>
        <div><dt>Hiện có (tháp tài sản, trừ quỹ dự phòng)</dt><dd>{view!.capital ? formatVnd(view!.capital) : "chưa nhập tháp tài sản"}</dd></div>
        {r.income_now && <div><dt>Dòng tiền hiện tại{view!.income ? " (tài sản thực trả)" : " (vốn × tỷ suất giả định)"}</dt><dd>~{formatVnd(r.income_now)}/tháng{r.progress ? ` · đạt ${formatRatio(r.progress, 1).replace(",0%", "%")} mục tiêu` : ""}</dd></div>}
        {view!.income && <ul className="perf-bench" aria-label="Dòng tiền hiện tại theo lớp">
          <li>Tiền gửi ({rate(view!.default_rate!)}%/năm): {formatVnd(view!.income.deposit)}/tháng</li>
          <li>Trái phiếu ({rate(view!.goal?.bond_rate ?? view!.default_bond_rate)}%/năm): {formatVnd(view!.income.bond)}/tháng</li>
          {view!.income.stocks !== undefined
            ? <li>Cổ phiếu ({rate(view!.goal!.stock_rate!)}%/năm, bạn nhập): {formatVnd(view!.income.stocks)}/tháng <span className="caption">(theo giá mua)</span></li>
            : <li>Cổ tức tiền mặt 12 tháng: {formatVnd(view!.income.dividends)}/tháng <span className="caption">(theo lịch sự kiện, số cổ phiếu đang nắm)</span></li>}
          <li>Vàng, tiền mặt, tiền số: không tạo dòng tiền</li>
        </ul>}
        <div className="eb-main"><dt>Đạt mục tiêu{Number(view!.contribution) > 0 ? ` (góp đều ${formatVnd(view!.contribution)}/tháng)` : " (không góp thêm)"}</dt>
          <dd data-testid="pi-when">{when(r)}</dd></div>
      </dl>}
    </section>
  );
}
