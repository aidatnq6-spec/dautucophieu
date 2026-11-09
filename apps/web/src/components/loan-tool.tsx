"use client";
import { type CSSProperties, type ReactNode, useMemo, useState } from "react";
import { Download, Printer, RotateCcw, TableProperties } from "lucide-react";
import { formatVnd } from "../lib/format";
import { download, spreadsheet } from "./journal-tools";
import { LoanStress, STRESS_DEFAULTS } from "./loan-stress";
import { loanSchedule, parseAmount, paymentStep, savedByPrepaying, shareText, type Loan, type LoanInput, type Method } from "./loan-calc";

type Unit = "ty" | "trieu";
type Span = "year" | "month";
const DEFAULTS = { mode: "loan" as "loan" | "property", loan: "2", loanUnit: "ty" as Unit, property: "3", propertyUnit: "ty" as Unit, ltv: "70", term: "25", termUnit: "year" as Span,
  promoRate: "7,5", promo: "1", promoUnit: "year" as Span, afterRate: "11", method: "declining" as Method, grace: "0", prepayOn: false, prepayMonth: "60", prepayFee: "2", ...STRESS_DEFAULTS };
type Form = typeof DEFAULTS;
type Blocked = { errors: string[] };
type Ready = { errors: string[]; loan: Loan; full: Loan; input: LoanInput; afterRate: number; principal: number; months: number; promoMonths: number; grace: number; upfront: number; ratio: number };

const num = (s: string) => { const t = s.trim().replace(",", "."); return /^\d+(\.\d+)?$/.test(t) ? Number(t) : null; };
const vnd = (v: number) => formatVnd(String(Math.round(v)));
const toMonths = (n: number | null, unit: Span) => (n === null ? null : unit === "year" ? n * 12 : n);
const spanText = (m: number) => (m % 12 === 0 ? `${m / 12} năm` : `${m} tháng`);
const INK = "var(--ink)", BLUE = "var(--brand)", AMBER = "var(--focus)";

function Slider({ label, value, onChange, min, max, step, unit, pick }: { label: string; value: string; onChange: (v: string) => void; min: number; max: number; step: number; unit?: string; pick?: ReactNode }) {
  const n = num(value.replace(/\.(?=\d{3}\b)/g, ""));
  const at = Math.min(Math.max(n ?? min, min), max);
  const scale = (v: number) => String(v).replace(".", ",");
  return (
    <div className="ln-slider">
      <div className="ln-slider-head">
        <label className="ln-value"><span>{label}</span><span className="ln-box"><input inputMode="decimal" value={value} onChange={(e) => onChange(e.target.value)} />{unit && <span className="ln-unit">{unit}</span>}</span></label>
        {pick}
      </div>
      <input type="range" aria-label={`Kéo: ${label}`} min={min} max={max} step={step} value={at} style={{ "--fill": `${((at - min) / (max - min)) * 100}%` } as CSSProperties} onChange={(e) => onChange(e.target.value.replace(".", ","))} />
      <div className="ln-scale" aria-hidden="true"><span>{scale(min)}</span><span>{scale(max)}</span></div>
    </div>
  );
}

function UnitPick<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: [T, string][]; onChange: (v: T) => void }) {
  return <select className="ln-pick" aria-label={label} value={value} onChange={(e) => onChange(e.target.value as T)}>{options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>;
}

function Donut({ parts, total, center }: { parts: { label: string; value: number; color: string }[]; total: number; center: number }) {
  const C = 2 * Math.PI * 80;
  const shown = parts.filter((p) => p.value > 0);
  const lengths = shown.map((p) => (total ? (p.value / total) * C : 0));
  return (
    <svg viewBox="0 0 200 200" className="ln-donut" role="img" aria-label={`Trả ngân hàng ${vnd(center)}: ${parts.map((p) => `${p.label} ${vnd(p.value)}`).join(", ")}`}>
      <g transform="rotate(-90 100 100)">{shown.map((p, i) => <circle key={p.label} cx="100" cy="100" r="80" fill="none" stroke={p.color} strokeWidth="14"
        strokeDasharray={`${Math.max(lengths[i] - 3, 0)} ${C}`} strokeDashoffset={-lengths.slice(0, i).reduce((a, b) => a + b, 0)} />)}</g>
      <text x="100" y="105" textAnchor="middle" className="ln-center">{vnd(center)}</text>
    </svg>
  );
}

/** Estimate of a loan's monthly payments. Runs in the browser; nothing is saved or sent anywhere. */
export function LoanTool() {
  const [f, setF] = useState<Form>(DEFAULTS);
  const [open, setOpen] = useState(false);
  const set = <K extends keyof Form>(key: K) => (value: Form[K]) => setF((old) => ({ ...old, [key]: value }));
  const result = useMemo<Blocked | Ready>(() => {
    const value = parseAmount(f.property, f.propertyUnit), ltv = num(f.ltv);
    const principal = f.mode === "loan" ? parseAmount(f.loan, f.loanUnit) : value !== null && ltv !== null ? (value * ltv) / 100 : null;
    const months = toMonths(num(f.term), f.termUnit), promoMonths = toMonths(num(f.promo), f.promoUnit);
    const promoRate = num(f.promoRate), afterRate = num(f.afterRate), grace = num(f.grace), prepayMonth = num(f.prepayMonth), fee = num(f.prepayFee);
    const errors: string[] = [];
    if (principal === null || principal <= 0) errors.push("Nhập giá trị khoản vay lớn hơn 0.");
    if (f.mode === "property" && (ltv === null || ltv <= 0 || ltv > 100)) errors.push("Tỉ lệ vay từ trên 0 đến 100%.");
    if (months === null || !Number.isInteger(months) || months < 1 || months > 600) errors.push("Thời hạn vay từ 1 tháng đến 50 năm, số nguyên tháng.");
    if (promoMonths === null || !Number.isInteger(promoMonths)) errors.push("Thời gian ưu đãi phải là số nguyên tháng.");
    else if (months !== null && promoMonths > months) errors.push("Thời gian ưu đãi không dài hơn thời hạn vay.");
    if (promoRate === null || promoRate > 100 || afterRate === null || afterRate > 100) errors.push("Lãi suất từ 0 đến 100%.");
    if (grace === null || !Number.isInteger(grace) || (months !== null && grace >= months)) errors.push("Ân hạn nợ gốc là số nguyên tháng, ngắn hơn thời hạn vay.");
    if (f.prepayOn && (prepayMonth === null || !Number.isInteger(prepayMonth) || prepayMonth < 1 || (months !== null && prepayMonth >= months))) errors.push("Tháng trả trước hạn phải nằm trong thời hạn vay, trước tháng cuối.");
    if (f.prepayOn && (fee === null || fee > 100)) errors.push("Phí trả trước hạn từ 0 đến 100%.");
    if (errors.length) return { errors };
    const base = { principal: principal!, months: months!, promoMonths: promoMonths!, promoRate: promoRate!, afterRate: afterRate!, method: f.method, graceMonths: grace! };
    const full = loanSchedule(base);
    const loan = f.prepayOn ? loanSchedule({ ...base, prepay: { month: prepayMonth!, feePercent: fee! } }) : full;
    return { errors: [], loan, full, input: base, afterRate: afterRate!, principal: principal!, months: months!, promoMonths: promoMonths!, grace: grace!, upfront: f.mode === "property" ? value! - principal! : 0, ratio: f.mode === "property" ? ltv! : 100 };
  }, [f]);
  const ok = "loan" in result ? result : null;
  function exportRows() {
    if (!ok) return;
    download(spreadsheet("LichTraNo", ["Kỳ", "Dư nợ đầu kỳ", "Trả gốc", "Trả lãi", "Phí trả trước", "Số tiền trả", "Dư nợ cuối kỳ", "Lãi suất (%/năm)"],
      ok.loan.rows.map((r) => [r.period, Math.round(r.opening), Math.round(r.principal), Math.round(r.interest), Math.round(r.fee), Math.round(r.payment), Math.round(r.closing), r.rate])), "lich-tra-no.xls");
  }
  const step = ok ? paymentStep(ok.loan, ok.promoMonths, ok.grace) : null;
  const parts = ok ? [{ label: "Cần trả trước", value: ok.upfront, color: INK }, { label: "Gốc cần trả", value: ok.principal, color: BLUE }, { label: "Lãi cần trả", value: ok.loan.interest + ok.loan.fee, color: AMBER }].filter((p) => p.value > 0) : [];
  const facts: [string, string][] = ok ? [
    ...(f.mode === "property" ? [["Giá trị bất động sản", vnd(ok.principal + ok.upfront)] as [string, string], ["Tỉ lệ vay", `${String(ok.ratio).replace(".", ",")}%`] as [string, string]] : []),
    ["Giá trị khoản vay", vnd(ok.principal)], ["Thời hạn vay", spanText(ok.months)],
    ["Lãi suất ưu đãi", `${f.promoRate}%/năm trong ${f.promo} ${f.promoUnit === "year" ? "năm" : "tháng"}`], ["Lãi suất sau ưu đãi", `${f.afterRate}%/năm`],
    ["Phương thức", f.method === "declining" ? "Dư nợ giảm dần" : "Trả đều hàng tháng"],
    ...(Number(f.grace) > 0 ? [["Ân hạn nợ gốc", `${f.grace} tháng`] as [string, string]] : []),
    ...(f.prepayOn ? [["Trả hết trước hạn", `cuối tháng thứ ${f.prepayMonth}, phí ${f.prepayFee}%`] as [string, string]] : []),
  ] : [];
  return (
    <div className="ln">
      <dl className="ln-print" aria-label="Thông tin khoản vay khi in">{facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
      <div className="ln-grid">
        <section className="surface ln-controls" aria-label="Thông tin khoản vay">
          <div className="ln-group">
            <h2>Khoản vay</h2>
            <div className="ln-radios" role="radiogroup" aria-label="Cách nhập khoản vay">
              <label><input type="radio" name="ln-mode" checked={f.mode === "loan"} onChange={() => set("mode")("loan")} /> Giá trị khoản vay</label>
              <label><input type="radio" name="ln-mode" checked={f.mode === "property"} onChange={() => set("mode")("property")} /> Giá trị bất động sản</label>
            </div>
            {f.mode === "loan"
              ? <Slider label="Giá trị khoản vay" value={f.loan} onChange={set("loan")} min={f.loanUnit === "ty" ? 0.1 : 100} max={f.loanUnit === "ty" ? 50 : 50000} step={f.loanUnit === "ty" ? 0.1 : 100}
                pick={<UnitPick label="Đơn vị" value={f.loanUnit} options={[["ty", "Tỷ"], ["trieu", "Triệu"]]} onChange={set("loanUnit")} />} />
              : <><Slider label="Giá trị bất động sản" value={f.property} onChange={set("property")} min={f.propertyUnit === "ty" ? 0.1 : 100} max={f.propertyUnit === "ty" ? 100 : 100000} step={f.propertyUnit === "ty" ? 0.1 : 100}
                pick={<UnitPick label="Đơn vị" value={f.propertyUnit} options={[["ty", "Tỷ"], ["trieu", "Triệu"]]} onChange={set("propertyUnit")} />} />
                <Slider label="Tỉ lệ vay" unit="%" value={f.ltv} onChange={set("ltv")} min={10} max={100} step={1} /></>}
            <Slider label="Thời hạn vay" value={f.term} onChange={set("term")} min={1} max={f.termUnit === "year" ? 35 : 420} step={1}
              pick={<UnitPick label="Tính theo" value={f.termUnit} options={[["year", "Năm"], ["month", "Tháng"]]} onChange={set("termUnit")} />} />
          </div>
          <div className="ln-group">
            <h2>Lãi suất</h2>
            <div className="ln-rates">
              <div>
                <h3>Giai đoạn ưu đãi</h3>
                <Slider label="Lãi suất ưu đãi" unit="%/năm" value={f.promoRate} onChange={set("promoRate")} min={0} max={25} step={0.1} />
                <Slider label="Thời gian ưu đãi" value={f.promo} onChange={set("promo")} min={0} max={f.promoUnit === "year" ? 10 : 120} step={1}
                  pick={<UnitPick label="Tính theo" value={f.promoUnit} options={[["year", "Năm"], ["month", "Tháng"]]} onChange={set("promoUnit")} />} />
              </div>
              <div>
                <h3>Sau ưu đãi</h3>
                <Slider label="Lãi suất sau ưu đãi" unit="%/năm" value={f.afterRate} onChange={set("afterRate")} min={0} max={25} step={0.1} />
              </div>
            </div>
          </div>
          <div className="ln-group">
            <h2>Phương thức tính lãi</h2>
            <div className="ln-radios" role="radiogroup" aria-label="Phương thức tính lãi">
              <label><input type="radio" name="ln-method" checked={f.method === "declining"} onChange={() => set("method")("declining")} /> Dư nợ giảm dần</label>
              <label><input type="radio" name="ln-method" checked={f.method === "annuity"} onChange={() => set("method")("annuity")} /> Trả đều hàng tháng</label>
            </div>
          </div>
          <div className="ln-group">
            <h2>Tùy chọn</h2>
            <Slider label="Ân hạn nợ gốc" unit="tháng" value={f.grace} onChange={set("grace")} min={0} max={60} step={1} />
            <label className="ln-check"><input type="checkbox" checked={f.prepayOn} onChange={(e) => set("prepayOn")(e.target.checked)} /> Trả hết nợ trước hạn</label>
            {f.prepayOn && <div className="ln-row"><Slider label="Trả hết vào cuối tháng thứ" value={f.prepayMonth} onChange={set("prepayMonth")} min={1} max={Math.max(ok ? ok.months - 1 : 420, 1)} step={1} />
              <label className="field">Phí trả trước hạn (%)<input inputMode="decimal" value={f.prepayFee} onChange={(e) => set("prepayFee")(e.target.value)} /></label></div>}
          </div>
          <button type="button" className="btn text ln-reset" onClick={() => { setF(DEFAULTS); setOpen(false); }}><RotateCcw size={14} aria-hidden="true" />Đặt lại</button>
        </section>
        <aside className="surface ln-result" aria-label="Kết quả khoản vay">
          {result.errors.length > 0 && <ul className="errors" role="alert">{result.errors.map((e) => <li key={e}>{e}</li>)}</ul>}
          {ok && <>
            {step
              ? <>
                <div className="ln-step">
                  <div><p className="caption">Trong ưu đãi · tháng đầu</p><p className="ln-amount" data-testid="ln-first">{vnd(step.first)}</p></div>
                  <div><p className="caption">Sau ưu đãi · tháng {step.period}</p><p className="ln-amount" data-testid="ln-after">{vnd(step.after)}</p></div>
                </div>
                <p className={`ln-rise ${step.rise > 0 ? "negative" : "positive"}`} data-testid="ln-rise">{step.rise > 0 ? "Tăng" : "Giảm"} {vnd(Math.abs(step.rise))} ({step.rise > 0 ? "+" : "−"}{shareText(Math.abs(step.rise), step.after - step.rise)}) so với tháng liền trước</p>
              </>
              : <><p className="caption">Thanh toán tháng đầu</p><p className="ln-first" data-testid="ln-first">{vnd(ok.loan.rows[0].payment)}</p></>}
            <p className="caption">Tỉ lệ vay {String(ok.ratio).replace(".", ",")}% · {spanText(ok.months)} · {String(ok.loan.rows[0].rate).replace(".", ",")}%/năm</p>
            <Donut parts={parts} total={ok.upfront + ok.loan.total} center={ok.loan.total} />
            <p className="caption">Giữa vòng: tổng trả ngân hàng (gốc, lãi, phí)</p>
            <dl className="ln-lines">
              {parts.map((p) => <div key={p.label}><dt><span className="ln-dot" style={{ background: p.color }} />{p.label}{p.label === "Lãi cần trả" && ok.loan.fee > 0 ? " (gồm phí)" : ""}</dt><dd>{vnd(p.value)} <span className="ln-share">{shareText(p.value, ok.upfront + ok.loan.total)}</span></dd></div>)}
              {ok.upfront > 0 && <div><dt>Tổng tiền bỏ ra (gồm trả trước)</dt><dd data-testid="ln-all">{vnd(ok.upfront + ok.loan.total)}</dd></div>}
              {ok.loan.fee > 0 && <div><dt>Trong đó phí trả trước hạn</dt><dd>{vnd(ok.loan.fee)}</dd></div>}
              {f.prepayOn && <div><dt>Tiết kiệm so với trả đủ hạn (đã trừ phí)</dt><dd data-testid="ln-saved">{vnd(savedByPrepaying(ok.full, ok.loan))}</dd></div>}
            </dl>
          </>}
          <div className="actions ln-actions">
            <button type="button" className="btn primary" aria-expanded={open} disabled={!ok} onClick={() => setOpen(!open)}><TableProperties size={16} aria-hidden="true" />Thanh toán từng tháng</button>
            <button type="button" className="btn" onClick={() => window.print()}><Printer size={16} aria-hidden="true" />In</button>
          </div>
        </aside>
      </div>
      {ok && <LoanStress input={ok.input} full={ok.full} afterRate={ok.afterRate} v={f} onField={(k, value) => setF((old) => ({ ...old, [k]: value }))} />}
      {ok && open && <section className="surface" aria-label="Lịch thanh toán từng tháng">
        <div className="row"><h2>Lịch thanh toán: {ok.loan.rows.length} kỳ</h2>
          <button type="button" className="btn" onClick={exportRows}><Download size={16} aria-hidden="true" />Xuất Excel</button></div>
        <div className="tablewrap"><table aria-label="Lịch thanh toán">
          <thead><tr><th>Kỳ</th><th className="num">Dư nợ đầu kỳ</th><th className="num">Trả gốc</th><th className="num">Trả lãi</th>{ok.loan.fee > 0 && <th className="num">Phí</th>}<th className="num">Số tiền trả</th><th className="num">Dư nợ cuối kỳ</th><th className="num">Lãi suất</th></tr></thead>
          <tbody>{ok.loan.rows.map((r) => <tr key={r.period}><td>{r.period}</td><td className="num">{vnd(r.opening)}</td><td className="num">{vnd(r.principal)}</td><td className="num">{vnd(r.interest)}</td>
            {ok.loan.fee > 0 && <td className="num">{vnd(r.fee)}</td>}<td className="num">{vnd(r.payment)}</td><td className="num">{vnd(r.closing)}</td><td className="num">{String(r.rate).replace(".", ",")}%</td></tr>)}</tbody>
        </table></div>
      </section>}
      <p className="caption">Ước tính: lãi mỗi tháng = dư nợ × lãi năm ÷ 12; ngân hàng thường tính theo số ngày thực tế, nên số thật lệch nhẹ từng tháng. Lãi suất do bạn nhập, chưa gồm phí và bảo hiểm khác của ngân hàng. Tính ngay trên trình duyệt, không lưu và không gửi đi đâu.</p>
    </div>
  );
}
