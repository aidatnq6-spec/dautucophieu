"use client";
import { useEffect, useRef, useState } from "react";
import { Target } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";
import { GrowthPath } from "./growth-path";

type Result = { required: string; income_now: string | null; progress: string | null; months: number | null; reached_on: string | null; rate: string };
type Income = { deposit: string; bond: string; dividends: string; stocks?: string; total: string; deposit_market_rate_count?: number;
  bond_default_rate_count?: number };
type Level = { id: "safe" | "independent" | "freedom"; spending: string | null; without_rent: string | null; with_rent: string | null; actual?: string | null };
type Levels = { rent: string; rent_missing: string[]; rows: Level[]; actual?: string | null; actual_months?: string[] };
type View = { version: number; levels?: Levels | null; goal: { target: string; rate: string | null; bond_rate: string; stock_rate?: string | null; independent?: string | null; freedom?: string | null } | null; default_rate: string | null; default_bond_rate: string;
  income: Income | null; result: Result | null; capital: string | null; contribution: string };

const rate = (v: string) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 2 });

function when(r: Result) {
  if (r.months === null) return "Chưa đạt trong 50 năm với giả định hiện tại";
  if (r.months === 0) return "Đã đạt";
  const years = Math.floor(r.months / 12), months = r.months % 12;
  const span = years ? `khoảng ${years} năm${months ? ` ${months} tháng` : ""}` : `khoảng ${months} tháng`;
  return `${span} (khoảng ${r.reached_on!.slice(5, 7)}/${r.reached_on!.slice(0, 4)})`;
}

const LEVEL: Record<Level["id"], [string, string]> = { safe: ["An toàn", "chưa nhập chi tiêu ở Sức khỏe tài chính"], independent: ["Độc lập", "chưa đặt"], freedom: ["Tự do", "chưa đặt"] };
const cover = (v: string | null) => (v === null ? "—" : formatRatio(v, 1).replace(",0%", "%"));

/** Capital needed for a monthly income at an assumed rate, the income today's capital would pay, and time to the goal. An estimate. */
export function PassiveIncome({ refresh }: { refresh?: string } = {}) {
  const [view, setView] = useState<View | null>(null);
  const [target, setTarget] = useState("");
  const [yieldRate, setYieldRate] = useState("");
  const [bondRate, setBondRate] = useState("");
  const [stockRate, setStockRate] = useState("");
  const [independent, setIndependent] = useState("");
  const [freedom, setFreedom] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const typed = useRef(false);  // a reload refreshes the figures; what is being typed stays
  useEffect(() => {
    let live = true;
    api<View>("passive-income").then((v) => {
      if (!live) return;
      setView(v);
      if (typed.current) return;
      if (v.goal) { setTarget(formatVnd(v.goal.target, { unit: false })); if (v.goal.rate) setYieldRate(v.goal.rate.replace(".", ",")); }
      setBondRate((v.goal?.bond_rate ?? v.default_bond_rate).replace(".", ","));
      if (v.goal?.stock_rate) setStockRate(v.goal.stock_rate.replace(".", ","));
      if (v.goal?.independent) setIndependent(formatVnd(v.goal.independent, { unit: false }));
      if (v.goal?.freedom) setFreedom(formatVnd(v.goal.freedom, { unit: false }));
    }, (e) => { if (live) setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."); });
    return () => { live = false; };
  }, [refresh]);
  async function save() {
    if (!view) return;
    const t = parseMoneyInput(target);
    const r = yieldRate.trim() ? parseMoneyInput(yieldRate) : null;  // empty = the 12-month deposit rate
    const b = bondRate.trim() ? parseMoneyInput(bondRate) : null;
    const s = stockRate.trim() ? parseMoneyInput(stockRate) : null;  // empty = last year's cash dividends
    if (t === null || t.includes(".") || (yieldRate.trim() && r === null)) { setMessage("Nhập dòng tiền mong muốn (đồng) và tỷ suất (%), hoặc để trống tỷ suất."); return; }
    const ind = independent.trim() ? parseMoneyInput(independent) : null, free = freedom.trim() ? parseMoneyInput(freedom) : null;
    if ((independent.trim() && (ind === null || ind.includes("."))) || (freedom.trim() && (free === null || free.includes(".")))) { setMessage("Mức độc lập và mức tự do: nhập số đồng, hoặc để trống."); return; }
    try {
      setView(await api<View>("passive-income", { method: "PUT", body: { target: t, rate: r, bond_rate: b, stock_rate: s, independent: ind, freedom: free, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      typed.current = false;
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const r = view?.result;
  return (
    <section className="surface" aria-label="Mục tiêu dòng tiền thụ động">
      <h2>Mục tiêu dòng tiền thụ động</h2>
      <p className="caption">Cần bao nhiêu vốn để tài sản tạo ra dòng tiền mỗi tháng như mong muốn, và với vốn hiện có (Tháp tài sản, trừ quỹ dự phòng) cộng
        góp đều mỗi tháng (Góp vốn đều), tái đầu tư ở cùng tỷ suất, thì khoảng bao lâu đạt. Dòng tiền hiện tại tính theo tài sản thực trả (tiền gửi, trái phiếu, cổ tức); vốn cần có và thời gian đạt dùng tỷ suất giả định. Ước tính đơn giản, theo tiền hôm nay, chưa tính lạm phát;
        không phải khuyến nghị.</p>
      <form className="eb-form" onInput={() => { typed.current = true; }} onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <label className="field">Dòng tiền mong muốn mỗi tháng (đ)<input inputMode="numeric" value={target} disabled={!view} onChange={(e) => setTarget(groupDigitsInput(e.target.value))} /></label>
        <label className="field">Tỷ suất dòng tiền giả định (%/năm)<input inputMode="decimal" value={yieldRate} disabled={!view} onChange={(e) => setYieldRate(e.target.value)}
          placeholder={view?.default_rate ? `để trống = lãi tiền gửi 12 tháng (${rate(view.default_rate)}%)` : "ví dụ 6"} /></label>
        <label className="field">Lãi suất trái phiếu (%/năm)<input inputMode="decimal" value={bondRate} disabled={!view} onChange={(e) => setBondRate(e.target.value)} /></label>
        <label className="field">Lợi suất cổ phiếu (%/năm)<input inputMode="decimal" value={stockRate} disabled={!view} onChange={(e) => setStockRate(e.target.value)}
          placeholder="để trống = cổ tức tiền mặt 12 tháng" /></label>
        <label className="field">Mức độc lập: chi tiêu mỗi tháng (đ)<input inputMode="numeric" value={independent} disabled={!view} onChange={(e) => setIndependent(groupDigitsInput(e.target.value))} /></label>
        <label className="field">Mức tự do: chi tiêu mỗi tháng (đ)<input inputMode="numeric" value={freedom} disabled={!view} onChange={(e) => setFreedom(groupDigitsInput(e.target.value))} /></label>
        <button type="submit" className="btn primary" disabled={!view}><Target size={16} aria-hidden="true" />Tính mục tiêu</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {view?.goal && !r && <p className="notice">Chưa có lãi tiền gửi 12 tháng ở trang Vĩ mô; nhập tỷ suất giả định để tính.</p>}
      {r && <dl className="eb-result">
        <div><dt>Vốn cần có (tỷ suất {rate(r.rate)}%/năm)</dt><dd data-testid="pi-required">{formatVnd(r.required)}</dd></div>
        <div><dt>Hiện có (tháp tài sản, trừ quỹ dự phòng)</dt><dd>{view!.capital ? formatVnd(view!.capital) : "chưa nhập tháp tài sản"}</dd></div>
        {r.income_now && <div><dt>Dòng tiền hiện tại{view!.income ? " (tài sản thực trả)" : " (vốn × tỷ suất giả định)"}</dt><dd>~{formatVnd(r.income_now)}/tháng{r.progress ? ` · đạt ${formatRatio(r.progress, 1).replace(",0%", "%")} mục tiêu` : ""}</dd></div>}
        {view!.income && <ul className="perf-bench" aria-label="Dòng tiền hiện tại theo lớp">
          {view!.income.deposit_market_rate_count === undefined
            ? <li>Tiền gửi ({rate(view!.default_rate!)}%/năm): {formatVnd(view!.income.deposit)}/tháng</li>
            : <li>Tiền gửi (lãi suất từng sổ): {formatVnd(view!.income.deposit)}/tháng{view!.income.deposit_market_rate_count > 0
              && <span className="caption"> ({view!.income.deposit_market_rate_count} sổ chưa nhập lãi suất, tính theo {rate(view!.default_rate!)}%/năm thị trường)</span>}</li>}
          {view!.income.bond_default_rate_count === undefined
            ? <li>Trái phiếu ({rate(view!.goal?.bond_rate ?? view!.default_bond_rate)}%/năm): {formatVnd(view!.income.bond)}/tháng</li>
            : <li>Trái phiếu (lợi suất từng dòng): {formatVnd(view!.income.bond)}/tháng{view!.income.bond_default_rate_count > 0
              && <span className="caption"> ({view!.income.bond_default_rate_count} dòng chưa nhập lợi suất, tính theo {rate(view!.goal?.bond_rate ?? view!.default_bond_rate)}%/năm)</span>}</li>}
          {view!.income.stocks !== undefined
            ? <li>Cổ phiếu ({rate(view!.goal!.stock_rate!)}%/năm, bạn nhập): {formatVnd(view!.income.stocks)}/tháng <span className="caption">(theo giá mua)</span></li>
            : <li>Cổ tức tiền mặt 12 tháng: {formatVnd(view!.income.dividends)}/tháng <span className="caption">(theo lịch sự kiện, số cổ phiếu đang nắm)</span></li>}
          <li>Vàng, tiền mặt, tiền số: không tạo dòng tiền</li>
        </ul>}
        <div className="eb-main"><dt>Đạt mục tiêu{Number(view!.contribution) > 0 ? ` (góp đều ${formatVnd(view!.contribution)}/tháng)` : " (không góp thêm)"}</dt>
          <dd data-testid="pi-when">{when(r)}</dd></div>
      </dl>}
      {view && (view.levels ? <section aria-label="Ba mức tự do tài chính">
        <h3>Ba mức tự do tài chính</h3>
        <p className="caption">Dòng tiền thụ động hiện tại đạt bao nhiêu % chi tiêu mỗi mức. Mức an toàn là chi tiêu ở Sức khỏe tài chính, hai mức còn lại do bạn đặt. Tách riêng tiền thuê vì khoản này có thể không đều; tiền thuê ({formatVnd(view.levels.rent)}/tháng) chưa trừ chi phí và trả nợ.</p>
        <table className="fv-table" aria-label="Mức chi tiêu và dòng tiền đạt được">
          <thead><tr><th>Mức</th><th className="num">Chi tiêu/tháng</th><th className="num">Không tính tiền thuê</th><th className="num">Có tiền thuê</th>{view.levels.actual && <th className="num">Thực nhận</th>}</tr></thead>
          <tbody>{view.levels.rows.map((x) => <tr key={x.id}><td data-label="Mức">{LEVEL[x.id][0]}</td><td data-label="Chi tiêu" className="num">{x.spending === null ? LEVEL[x.id][1] : formatVnd(x.spending)}</td>
            <td data-label="Không tính tiền thuê" className="num">{cover(x.without_rent)}</td><td data-label="Có tiền thuê" className="num">{cover(x.with_rent)}</td>{view.levels!.actual && <td data-label="Thực nhận" className="num">{cover(x.actual ?? null)}</td>}</tr>)}</tbody>
        </table>
        {view.levels.actual && <p className="caption" data-testid="pi-actual">Thực nhận: trung bình {formatVnd(view.levels.actual)}/tháng thu nhập trả đều (tiền thuê, lãi tiền gửi, trái phiếu) trong {view.levels.actual_months?.length} tháng gần nhất ở Thu chi hằng tháng.</p>}
        {view.levels.rent_missing.length > 0 && <p className="notice">Chưa nhập tiền thuê nên chưa tính: {view.levels.rent_missing.join(", ")}.</p>}
      </section> : <p className="caption">Ba mức tự do tài chính: cần Tháp tài sản và lãi tiền gửi 12 tháng để tính dòng tiền hiện tại.</p>)}
      {r && (view!.capital
        ? <GrowthPath key={r.rate} capital={Number(view!.capital)} monthly={Number(view!.contribution)} rate={Number(r.rate)} required={Number(r.required)} />
        : <p className="caption">Nhập Tháp tài sản để xem đường tăng trưởng tài sản.</p>)}
    </section>
  );
}
