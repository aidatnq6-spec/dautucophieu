"use client";
import { formatVnd } from "../lib/format";
import { cashflowAfterLoan, parseAmount, shareText, stressLoan, type Loan, type LoanInput } from "./loan-calc";

export const STRESS_DEFAULTS = { customRate: "", income: "", extra: "", expense: "", reserve: "", ceiling: "40" };
export type StressFields = typeof STRESS_DEFAULTS;
type Key = keyof StressFields;

const STEPS = [0, 2, 4, 6];
const vnd = (v: number) => formatVnd(String(Math.round(v)));
const num = (s: string) => { const t = s.trim().replace(",", "."); return /^\d+(\.\d+)?$/.test(t) ? Number(t) : null; };
const trieu = (s: string) => (s.trim() === "" ? null : parseAmount(s, "trieu"));
const rateText = (r: number) => `${String(Math.round(r * 100) / 100).replace(".", ",")}%`;
const times = (v: number | null) => (v === null ? "—" : `${v.toFixed(2).replace(".", ",")} lần`);

function Money({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return <label className="field">{label}<input inputMode="decimal" value={value} onChange={(e) => onChange(e.target.value)} /></label>;
}

/** Thử sức chịu lãi suất and Dòng tiền sau khi vay. In the browser only, like the rest of the page: what is typed here is neither saved nor sent. */
export function LoanStress({ input, full, afterRate, v, onField }: { input: LoanInput; full: Loan; afterRate: number; v: StressFields; onField: (k: Key, value: string) => void }) {
  const custom = v.customRate.trim() === "" ? null : num(v.customRate);
  const customBad = v.customRate.trim() !== "" && (custom === null || custom > 100);
  const salary = trieu(v.income), extra = trieu(v.extra), expense = trieu(v.expense), reserve = trieu(v.reserve), ceiling = num(v.ceiling);
  const unread = ([["Thu nhập", v.income, salary], ["Thu nhập thêm", v.extra, extra], ["Chi tiêu", v.expense, expense], ["Tiền dự phòng", v.reserve, reserve]] as [string, string, number | null][])
    .filter(([, raw, parsed]) => raw.trim() !== "" && parsed === null).map(([name]) => name);
  const ceilingOk = ceiling !== null && ceiling > 0 && ceiling <= 100;
  const income = salary !== null && salary + (extra ?? 0) > 0 ? salary + (extra ?? 0) : null;
  const rates = [...STEPS.map((s) => afterRate + s), ...(custom !== null && !customBad ? [custom] : [])];
  const rows = stressLoan(input, rates);
  const flow = income === null ? null : cashflowAfterLoan(full, { income, expense, reserve });
  const over = flow !== null && ceilingOk && flow.peakRatio * 100 > ceiling;
  const pct = (r: number) => shareText(r, 1);
  return (
    <>
      <section className="surface" aria-label="Thử sức chịu lãi suất">
        <h2>Thử sức chịu lãi suất</h2>
        <p className="caption">Đổi lãi suất sau ưu đãi, giữ nguyên lãi ưu đãi, và tính khi trả đủ hạn. Đây là các kịch bản để thử, không phải dự báo lãi suất.</p>
        <div className="tablewrap"><table aria-label="Thử sức chịu lãi suất">
          <thead><tr><th>Lãi sau ưu đãi</th><th className="num">Khoản trả cao nhất</th><th className="num">So với tháng đầu</th><th className="num">Tiền lãi khi hết ưu đãi</th><th className="num">Tổng tiền lãi</th>{income !== null && <th className="num">Trả nợ / thu nhập</th>}</tr></thead>
          <tbody>{rows.map((r, i) => {
            const share = income === null ? null : r.peak / income;
            const label = i < STEPS.length ? (STEPS[i] === 0 ? "bạn nhập" : `+${STEPS[i]} điểm %`) : "tự chọn";
            return <tr key={`${label}-${r.rate}`}><td>{rateText(r.rate)} <span className="caption">{label}</span></td><td className="num">{vnd(r.peak)} <span className="caption">tháng {r.peakPeriod}</span></td><td className="num">{times(r.times)}</td><td className="num">{r.interestTimes === null ? "—" : `gấp ${times(r.interestTimes)}`}</td><td className="num">{vnd(r.interest)}</td>
              {share !== null && <td className={`num${ceilingOk && share * 100 > ceiling ? " negative" : ""}`}>{pct(share)}{ceilingOk && share * 100 > ceiling ? " · vượt ngưỡng" : ""}</td>}</tr>;
          })}</tbody>
        </table></div>
        <label className="field ln-custom">Mức lãi tự chọn (%/năm)<input inputMode="decimal" value={v.customRate} aria-invalid={customBad} onChange={(e) => onField("customRate", e.target.value)} />{customBad && <span className="error">Lãi suất từ 0 đến 100%.</span>}</label>
      </section>
      <section className="surface" aria-label="Dòng tiền sau khi vay">
        <h2>Dòng tiền sau khi vay</h2>
        <div className="formgrid">
          <Money label="Thu nhập mỗi tháng (triệu đ)" value={v.income} onChange={(x) => onField("income", x)} />
          <Money label="Thu nhập thêm nếu có (triệu đ)" value={v.extra} onChange={(x) => onField("extra", x)} />
          <Money label="Chi tiêu mỗi tháng (triệu đ)" value={v.expense} onChange={(x) => onField("expense", x)} />
          <Money label="Tiền dự phòng (triệu đ)" value={v.reserve} onChange={(x) => onField("reserve", x)} />
          <Money label="Ngưỡng cảnh báo trả nợ (% thu nhập)" value={v.ceiling} onChange={(x) => onField("ceiling", x)} />
        </div>
        {unread.length > 0 && <ul className="errors" role="alert"><li>Chưa đọc được: {unread.join(", ")}. Nhập số triệu đồng, ví dụ 15 hoặc 15,5.</li></ul>}
        {!ceilingOk && <ul className="errors" role="alert"><li>Ngưỡng cảnh báo từ trên 0 đến 100%.</li></ul>}
        {flow === null ? <p className="muted ln-flow-empty">Nhập thu nhập lớn hơn 0 để xem phần còn lại sau khi trả nợ.</p> : <>
          {over && <p className="notice ln-flow-note" data-testid="ln-over">Khoản trả cao nhất chiếm {pct(flow.peakRatio)} thu nhập, vượt ngưỡng {String(ceiling).replace(".", ",")}% bạn đặt.</p>}
          <dl className="ln-flow">
            <div><dt>Trả nợ / thu nhập</dt><dd data-testid="ln-ratio">{pct(flow.firstRatio)} tháng đầu · {pct(flow.peakRatio)} cao nhất (tháng {flow.peakPeriod})</dd></div>
            <div><dt>Còn lại sau chi tiêu và trả nợ</dt><dd data-testid="ln-left">{flow.firstLeft === null ? "Chưa nhập chi tiêu" : <>{vnd(flow.firstLeft)} tháng đầu · <span className={flow.worstLeft! < 0 ? "negative" : undefined}>{vnd(flow.worstLeft!)}</span> tháng thấp nhất</>}</dd></div>
            <div><dt>Tháng đầu tiên bị âm</dt><dd data-testid="ln-negative">{flow.firstLeft === null ? "Chưa nhập chi tiêu" : flow.firstNegative === null ? "Không có tháng nào âm" : `Tháng ${flow.firstNegative}`}</dd></div>
            <div><dt>Tiền dự phòng</dt><dd data-testid="ln-reserve">{flow.firstLeft === null ? "Chưa nhập chi tiêu" : flow.firstNegative === null ? "Chưa phải dùng đến" : flow.reserve === null ? "Chưa nhập tiền dự phòng" : flow.reserve.runsOut === null ? "Đủ bù mọi tháng âm" : `Trụ được ${flow.reserve.covered} tháng, hết vào tháng ${flow.reserve.runsOut}`}</dd></div>
          </dl>
          <p className="caption">Tính khi trả đủ hạn, thu nhập và chi tiêu giữ nguyên suốt thời gian vay. Tiền dự phòng chỉ dùng để bù các tháng âm, tháng dư sau đó không cộng lại. Ngưỡng do bạn đặt, không phải quy định của ngân hàng.</p>
        </>}
      </section>
    </>
  );
}
