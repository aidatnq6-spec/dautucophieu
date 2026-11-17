"use client";
import { useEffect, useState } from "react";
import { formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";
import { buildingPlan, measureOf, scenario, sensitivity, type BuildingInput, type BuildingPlan, type Measure } from "./building-calc";
import type { Method } from "./loan-calc";

const DRAFT_KEY = "building-tool-draft-v1";
const OCCUPANCIES = [50, 60, 70, 80, 90, 100];
const RENT_PCTS = [-20, -10, 0, 10];
const MEASURES: [Measure, string][] = [["noi", "Lợi nhuận vận hành"], ["buy", "Nếu mua: dòng tiền sau trả nợ"], ["lease", "Nếu thuê lại: lợi nhuận sau tiền thuê tòa"]];
type Row = { name: string; count: string; price: string; life: string };
const EMPTY = {
  rooms: "", hiMonths: "", hiRent: "", hiOcc: "", loMonths: "", loRent: "", loOcc: "", peakRent: "",
  brokerPct: "", otaPct: "", otaShare: "", vatPct: "", pitPct: "", otherPct: "", reservePct: "",
  cleaning: "", common: "", staff: "", internet: "", insurance: "", fixedOther: "", pcccCost: "", pcccYears: "",
  price: "", buyCosts: "", renovation: "", own: "", loanRate: "", termYears: "",
  leaseRent: "", deposit: "", setup: "", leaseMonths: "",
  badOcc: "", badRent: "", goodOcc: "", goodRent: "",
};
type Key = keyof typeof EMPTY;
const MONEY = new Set<Key>(["hiRent", "loRent", "peakRent", "cleaning", "common", "staff", "internet", "insurance", "fixedOther", "pcccCost",
  "price", "buyCosts", "renovation", "own", "leaseRent", "deposit", "setup"]);

const SIGNED = new Set<Key>(["badOcc", "badRent", "goodOcc", "goodRent"]);
const signedNum = (s: string) => (s.trim() ? Number(s.trim().replace(/\s/g, "").replace("−", "-").replace(",", ".")) : null);
const money = (s: string) => (s.trim() ? Number(parseMoneyInput(s) ?? NaN) : 0);
const num = (s: string) => (s.trim() ? Number(s.trim().replace(/\./g, "").replace(",", ".")) : 0);
const vnd = (v: number) => formatVnd(String(Math.round(v)));
const pct = (v: number) => formatRatio(v.toFixed(6), 1);

function Field({ k, label, f, set, hint }: { k: Key; label: string; f: typeof EMPTY; set: (k: Key, v: string) => void; hint?: string }) {
  return <label className="field">{label}<input aria-label={label} inputMode={MONEY.has(k) ? "numeric" : "decimal"} value={f[k]} placeholder={hint}
    onChange={(e) => set(k, MONEY.has(k) ? groupDigitsInput(e.target.value) : e.target.value)} /></label>;
}

function Scenarios({ input, base, f, set }: { input: BuildingInput; base: BuildingPlan; f: typeof EMPTY; set: (k: Key, v: string) => void }) {
  const [measure, setMeasure] = useState<Measure>("noi");
  const shown = MEASURES.filter(([m]) => measureOf(base, m) !== null);
  const m = shown.some(([x]) => x === measure) ? measure : "noi";
  const cases = ([["Xấu", "badOcc", "badRent"], ["Tốt", "goodOcc", "goodRent"]] as [string, Key, Key][])
    .map(([name, o, r]) => [name, signedNum(f[o]), signedNum(f[r])] as const)
    .filter(([, o, r]) => o !== null || r !== null)
    .filter(([, o, r]) => !Number.isNaN(o ?? 0) && !Number.isNaN(r ?? 0))
    .map(([name, o, r]) => [name, scenario(input, o ?? 0, r ?? 0)] as const);
  const table = sensitivity(input, OCCUPANCIES, RENT_PCTS, m);
  const box = (k: Key, label: string) => <label className="field">{label}<input aria-label={label} inputMode="decimal" placeholder="ví dụ −10"
    value={f[k]} onChange={(e) => set(k, e.target.value)} /></label>;
  const cell = (v: number | null) => v === null ? "—" : <span className={v < 0 ? "negative" : undefined}>{vnd(v)}</span>;
  return (
    <section className="surface" aria-label="Kịch bản và độ nhạy">
      <h2>Kịch bản và độ nhạy</h2>
      <div className="actions" role="radiogroup" aria-label="Kết quả để so">{shown.map(([id, label]) => (
        <label key={id} className="choice"><input type="radio" name="bt-measure" checked={m === id} onChange={() => setMeasure(id)} />{label}</label>))}</div>
      <p className="caption">Kịch bản điều chỉnh so với số đã nhập ở trên: tỷ lệ có khách cộng/trừ điểm % ở mọi mùa (giữ trong 0–100%), giá thuê tăng/giảm %. Để trống thì
        không có kịch bản đó.</p>
      <div className="formgrid">{box("badOcc", "Kịch bản xấu: có khách ± (điểm %)")}{box("badRent", "Kịch bản xấu: giá thuê ± (%)")}
        {box("goodOcc", "Kịch bản tốt: có khách ± (điểm %)")}{box("goodRent", "Kịch bản tốt: giá thuê ± (%)")}</div>
      <table className="fv-table" aria-label="Ba kịch bản"><thead><tr><th>Kịch bản</th><th className="num">Doanh thu/tháng</th>
        <th className="num">{MEASURES.find(([x]) => x === m)![1]} (mỗi tháng)</th></tr></thead>
        <tbody>{[...cases.filter(([n]) => n === "Xấu"), ["Cơ sở", base] as const, ...cases.filter(([n]) => n === "Tốt")].map(([name, plan]) => (
          <tr key={name}><td>{name}</td><td className="num">{vnd(plan.revenueMonth)}</td><td className="num">{cell(measureOf(plan, m))}</td></tr>))}</tbody></table>
      <h3>Độ nhạy: {MEASURES.find(([x]) => x === m)![1].toLowerCase()} mỗi tháng</h3>
      <p className="caption">Mỗi hàng là một tỷ lệ có khách áp cho cả năm; mỗi cột là giá thuê thay đổi so với giá đã nhập. Ô đỏ là âm.</p>
      <div className="tablewrap"><table className="fv-table" aria-label="Bảng độ nhạy theo tỷ lệ có khách và giá thuê">
        <thead><tr><th>Có khách cả năm</th>{RENT_PCTS.map((r) => <th key={r} className="num">Giá {r === 0 ? "như đã nhập" : `${r > 0 ? "+" : "−"}${Math.abs(r)}%`}</th>)}</tr></thead>
        <tbody>{OCCUPANCIES.map((o, i) => <tr key={o}><td>{o}%</td>{table[i].map((v, j) => <td key={j} className="num">{cell(v)}</td>)}</tr>)}</tbody>
      </table></div>
    </section>
  );
}

/** Tính lợi nhuận tòa nhà cho thuê: revenue by season, the costs that follow it, the fixed and hidden ones, then buying or leasing the
 * building. Runs in the browser; the draft is kept in this browser only. */
export function BuildingTool() {
  const [f, setF] = useState(EMPTY);
  const [rows, setRows] = useState<Row[]>([{ name: "", count: "", price: "", life: "" }]);
  const [method, setMethod] = useState<Method>("annuity");
  const [restored, setRestored] = useState(false);
  useEffect(() => {
    void Promise.resolve().then(() => {  // the draft kept in this browser, once, after the first paint
      try {
        const kept = JSON.parse(window.localStorage.getItem(DRAFT_KEY) ?? "null");
        if (kept?.f) { setF({ ...EMPTY, ...kept.f }); setRows((old) => (kept.rows?.length ? kept.rows : old)); setMethod(kept.method ?? "annuity"); }
      } catch { /* no storage: start empty */ }
      setRestored(true);
    });
  }, []);
  useEffect(() => {
    if (!restored) return;
    try { window.localStorage.setItem(DRAFT_KEY, JSON.stringify({ f, rows, method })); } catch { /* not kept */ }
  }, [f, rows, method, restored]);
  const set = (k: Key, v: string) => setF((old) => ({ ...old, [k]: v }));
  const setRow = (i: number, k: keyof Row, v: string) => setRows((old) => old.map((r, j) => (j === i ? { ...r, [k]: k === "price" ? groupDigitsInput(v) : v } : r)));

  const compute = (): { error: string } | { plan: BuildingPlan; input: BuildingInput } | null => {
    const rooms = num(f.rooms);
    if (!rooms || (!f.hiRent.trim() && !f.loRent.trim())) return null;
    const values = Object.fromEntries((Object.keys(EMPTY) as Key[]).filter((k) => !SIGNED.has(k))
      .map((k) => [k, MONEY.has(k) ? money(f[k]) : num(f[k])])) as Record<Key, number>;
    if (Object.values(values).some((v) => Number.isNaN(v) || v < 0)) return { error: "Các ô chỉ nhận số không âm." };
    if (!Number.isInteger(rooms)) return { error: "Số phòng là số nguyên." };
    for (const k of ["hiOcc", "loOcc", "brokerPct", "otaPct", "otaShare", "vatPct", "pitPct", "otherPct", "reservePct"] as Key[])
      if (values[k] > 100) return { error: "Các tỷ lệ % từ 0 đến 100." };
    const equipment = rows.filter((r) => r.count.trim() || r.price.trim()).map((r) => ({ name: r.name, count: num(r.count), price: money(r.price), lifeYears: num(r.life) }));
    if (equipment.some((e) => Number.isNaN(e.count) || Number.isNaN(e.price) || !e.lifeYears)) return { error: "Mỗi thiết bị cần số lượng, giá và tuổi thọ (năm)." };
    const input: BuildingInput = {
      rooms, peakRent: values.peakRent || null,
      seasons: [{ months: values.hiMonths, rent: values.hiRent, occupancy: values.hiOcc }, { months: values.loMonths, rent: values.loRent, occupancy: values.loOcc }]
        .filter((s) => s.months > 0),
      brokerPct: values.brokerPct, otaPct: values.otaPct, otaShare: values.otaShare, vatPct: values.vatPct, pitPct: values.pitPct, otherPct: values.otherPct,
      reservePct: values.reservePct,
      fixed: { cleaning: values.cleaning, common: values.common, staff: values.staff, internet: values.internet, insurance: values.insurance, other: values.fixedOther },
      equipment, pccc: { cost: values.pcccCost, years: values.pcccYears },
      buy: values.price > 0 ? { price: values.price, buyCosts: values.buyCosts, renovation: values.renovation, own: values.own, loanRate: values.loanRate,
        termYears: values.termYears, method } : undefined,
      lease: values.leaseRent > 0 ? { rent: values.leaseRent, deposit: values.deposit, setup: values.setup, months: values.leaseMonths } : undefined,
    };
    if (!input.seasons.length) return { error: "Nhập số tháng của ít nhất một mùa." };
    if (input.buy && input.buy.own > input.buy.price + input.buy.buyCosts + input.buy.renovation) return { error: "Vốn tự có lớn hơn tổng tiền mua và sửa sang." };
    if (input.buy && input.buy.price + input.buy.buyCosts + input.buy.renovation > input.buy.own && (!input.buy.termYears || !Number.isInteger(input.buy.termYears)))
      return { error: "Có vay thì nhập thời hạn vay (số năm nguyên)." };
    return { plan: buildingPlan(input), input };
  };
  const out = compute();  // light arithmetic: worked out on each render
  const p = out && "plan" in out ? out.plan : null;
  const input = out && "input" in out ? out.input : null;
  const F = (k: Key, label: string, hint?: string) => <Field k={k} label={label} f={f} set={set} hint={hint} />;
  return (
    <>
    <div className="bt">
      <div className="bt-inputs">
        <section className="surface" aria-label="Doanh thu theo mùa">
          <h2>1. Doanh thu theo mùa</h2>
          <p className="caption">Giá thuê một phòng mỗi tháng và tỷ lệ phòng có khách trong từng mùa. Hai mùa cộng lại nên đủ 12 tháng.</p>
          <div className="formgrid">{F("rooms", "Số phòng")}{F("peakRent", "Giá cao nhất môi giới đưa (đ/phòng/tháng)", "để so")}</div>
          <div className="formgrid">{F("hiMonths", "Mùa cao điểm: số tháng")}{F("hiRent", "Giá (đ/phòng/tháng)")}{F("hiOcc", "Có khách (%)")}</div>
          <div className="formgrid">{F("loMonths", "Mùa thấp điểm: số tháng")}{F("loRent", "Giá thấp điểm (đ/phòng/tháng)")}{F("loOcc", "Có khách thấp điểm (%)")}</div>
        </section>
        <section className="surface" aria-label="Chi phí theo doanh thu">
          <h2>2. Chi phí tính theo % doanh thu</h2>
          <div className="formgrid">{F("brokerPct", "Hoa hồng môi giới, mạng xã hội (%)")}{F("otaPct", "Hoa hồng OTA (%)")}{F("otaShare", "Phần doanh thu qua OTA (%)")}</div>
          <div className="formgrid">{F("vatPct", "Thuế GTGT (%)")}{F("pitPct", "Thuế TNCN (%)")}{F("otherPct", "Chi phí khác (%)")}{F("reservePct", "Dự phòng rủi ro (%)")}</div>
          <p className="caption">Thuế cho thuê tùy hình thức kinh doanh và mức doanh thu: nhập theo trường hợp của bạn.</p>
        </section>
        <section className="surface" aria-label="Chi phí cố định">
          <h2>3. Chi phí cố định mỗi tháng (đ)</h2>
          <div className="formgrid">{F("cleaning", "Vệ sinh tổng thể")}{F("common", "Điện nước khu vực chung")}{F("staff", "Nhân sự quản lý, lễ tân")}</div>
          <div className="formgrid">{F("internet", "Internet, truyền hình")}{F("insurance", "Bảo hiểm")}{F("fixedOther", "Khác")}</div>
        </section>
        <section className="surface" aria-label="Chi phí chìm">
          <h2>4. Chi phí chìm</h2>
          <p className="caption">Thiết bị phải thay theo tuổi thọ (điều hòa, bình nóng lạnh, đèn, thiết bị vệ sinh…) và giấy PCCC, chia đều theo tháng.</p>
          {rows.map((r, i) => <div className="formgrid" key={i} role="group" aria-label={`Thiết bị ${i + 1}`}>
            <label className="field">Thiết bị<input aria-label={`Tên thiết bị ${i + 1}`} value={r.name} onChange={(e) => setRow(i, "name", e.target.value)} /></label>
            <label className="field">Số lượng<input aria-label={`Số lượng thiết bị ${i + 1}`} inputMode="numeric" value={r.count} onChange={(e) => setRow(i, "count", e.target.value)} /></label>
            <label className="field">Giá một cái (đ)<input aria-label={`Giá thiết bị ${i + 1}`} inputMode="numeric" value={r.price} onChange={(e) => setRow(i, "price", e.target.value)} /></label>
            <label className="field">Tuổi thọ (năm)<input aria-label={`Tuổi thọ thiết bị ${i + 1}`} inputMode="decimal" value={r.life} onChange={(e) => setRow(i, "life", e.target.value)} /></label>
            {rows.length > 1 && <button type="button" className="btn text" onClick={() => setRows(rows.filter((_, j) => j !== i))}>Bỏ</button>}
          </div>)}
          <button type="button" className="btn" onClick={() => setRows([...rows, { name: "", count: "", price: "", life: "" }])}>Thêm thiết bị</button>
          <div className="formgrid">{F("pcccCost", "Chi phí làm giấy PCCC (đ)")}{F("pcccYears", "Dùng trong (năm)")}</div>
        </section>
        <section className="surface" aria-label="Nếu mua tòa">
          <h2>5. Nếu mua tòa nhà</h2>
          <div className="formgrid">{F("price", "Giá mua (đ)")}{F("buyCosts", "Thuế phí sang tên (đ)")}{F("renovation", "Sửa sang, nội thất (đ)")}{F("own", "Vốn tự có (đ)")}</div>
          <div className="formgrid">{F("loanRate", "Lãi vay (%/năm)")}{F("termYears", "Thời hạn vay (năm)")}
            <label className="field">Cách trả<select aria-label="Cách trả khoản vay mua tòa" value={method} onChange={(e) => setMethod(e.target.value as Method)}>
              <option value="annuity">Trả đều hàng tháng</option><option value="declining">Dư nợ giảm dần</option></select></label></div>
        </section>
        <section className="surface" aria-label="Nếu thuê lại nguyên tòa">
          <h2>6. Nếu thuê lại nguyên tòa để vận hành</h2>
          <div className="formgrid">{F("leaseRent", "Tiền thuê nguyên tòa (đ/tháng)")}{F("deposit", "Tiền cọc (đ)")}{F("setup", "Chi phí setup ban đầu (đ)")}{F("leaseMonths", "Thời hạn hợp đồng (tháng)")}</div>
        </section>
      </div>
      <aside className="surface bt-result" aria-label="Kết quả lợi nhuận tòa nhà" aria-live="polite">
        <h2>Kết quả</h2>
        {!out && <p className="muted">Nhập số phòng và giá thuê để bắt đầu tính.</p>}
        {out && "error" in out && <p className="errors" role="alert">{out.error}</p>}
        {p && <>
          {p.monthsCheck !== 12 && <p className="notice">Hai mùa đang cộng thành {p.monthsCheck} tháng, chưa đủ 12: doanh thu năm tính theo số tháng đã nhập.</p>}
          <dl className="bt-list">
            <dt>Doanh thu bình quân mỗi tháng</dt><dd><strong>{vnd(p.revenueMonth)}</strong></dd>
            <dt>Doanh thu cả năm</dt><dd>{vnd(p.revenueYear)}</dd>
            <dt>Mất vì trống phòng</dt><dd>{vnd(p.vacancyLossYear)} một năm ({pct(p.vacancyShare)} doanh thu nếu kín phòng)</dd>
            {p.peakOverstates !== null && <><dt>Giá cao nhất × 12 tháng</dt><dd className="negative">cao hơn doanh thu thực tế {pct(p.peakOverstates)}</dd></>}
          </dl>
          <h3>Chi phí mỗi tháng</h3>
          <table className="fv-table" aria-label="Chi phí vận hành mỗi tháng"><tbody>
            {([["Hoa hồng bán phòng", p.costs.commission], ["Thuế", p.costs.tax], ["Chi phí khác theo doanh thu", p.costs.other], ["Dự phòng rủi ro", p.costs.reserve],
              ["Chi phí cố định", p.costs.fixed], ["Khấu hao thiết bị", p.costs.equipment], ["Giấy PCCC", p.costs.pccc]] as [string, number][])
              .filter(([, v]) => v > 0).map(([label, v]) => <tr key={label}><td>{label}</td><td className="num">{vnd(v)}</td>
                <td className="num">{p.revenueMonth > 0 ? pct(v / p.revenueMonth) : "—"}</td></tr>)}
            <tr><td><strong>Tổng chi phí</strong></td><td className="num"><strong>{vnd(p.costs.total)}</strong></td><td className="num"><strong>{pct(p.costShare)}</strong></td></tr>
          </tbody></table>
          <p className="caption">Tham khảo: bài ghi âm ngày 17/11/2026 về căn hộ dịch vụ Đà Nẵng ước tổng chi phí vận hành khoảng 33–43% doanh thu (chia sẻ cá nhân, không phải số liệu thống kê).</p>
          <dl className="bt-list"><dt>Lợi nhuận vận hành mỗi tháng (trước tiền vay hoặc tiền thuê tòa)</dt>
            <dd><strong className={p.noiMonth < 0 ? "negative" : undefined}>{vnd(p.noiMonth)}</strong></dd></dl>
          {p.buy && <section aria-label="Kết quả nếu mua tòa"><h3>Nếu mua tòa</h3><dl className="bt-list">
            <dt>Tổng tiền bỏ ra</dt><dd>{vnd(p.buy.invested)}{p.buy.loan > 0 && <> (vay {vnd(p.buy.loan)})</>}</dd>
            {p.buy.loan > 0 && <><dt>Trả ngân hàng mỗi tháng (bình quân năm đầu)</dt><dd>{vnd(p.buy.loanPaymentMonth)}</dd></>}
            <dt>Dòng tiền còn lại mỗi tháng</dt><dd><strong className={p.buy.cashMonth < 0 ? "negative" : undefined}>{vnd(p.buy.cashMonth)}</strong></dd>
            <dt>Lợi suất ròng trên tổng tiền bỏ ra</dt><dd>{pct(p.buy.netYield)} một năm</dd>
            {p.buy.cashOnCash !== null && <><dt>Lợi suất trên vốn tự có</dt><dd>{pct(p.buy.cashOnCash)} một năm</dd></>}
            <dt>Hoàn vốn tự có</dt><dd>{p.buy.paybackYears !== null ? `khoảng ${p.buy.paybackYears.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} năm` : "không hoàn vốn (dòng tiền âm)"}</dd>
            <dt>Tỷ lệ có khách tối thiểu để không âm tiền</dt><dd>{Number.isFinite(p.buy.breakevenOccupancy) ? pct(p.buy.breakevenOccupancy) : "không đạt được"}</dd>
          </dl></section>}
          {p.lease && <section aria-label="Kết quả nếu thuê lại nguyên tòa"><h3>Nếu thuê lại nguyên tòa</h3><dl className="bt-list">
            <dt>Doanh thu hòa vốn mỗi tháng</dt><dd><strong>{Number.isFinite(p.lease.breakevenRevenue) ? vnd(p.lease.breakevenRevenue) : "không đạt được"}</strong>
              {Number.isFinite(p.lease.multiple) && <> (gấp {p.lease.multiple.toLocaleString("vi-VN", { maximumFractionDigits: 2 })} lần tiền thuê tòa)</>}</dd>
            <dt>Tỷ lệ có khách tối thiểu</dt><dd className={p.lease.breakevenOccupancy > 1 ? "negative" : undefined}>
              {Number.isFinite(p.lease.breakevenOccupancy) ? pct(p.lease.breakevenOccupancy) : "không đạt được"}{p.lease.breakevenOccupancy > 1 && " — kín phòng cũng chưa hòa vốn"}</dd>
            <dt>Lợi nhuận mỗi tháng</dt><dd><strong className={p.lease.profitMonth < 0 ? "negative" : undefined}>{vnd(p.lease.profitMonth)}</strong></dd>
            <dt>Lợi nhuận cả hợp đồng (trừ chi phí setup)</dt><dd className={p.lease.contractProfit < 0 ? "negative" : undefined}>{vnd(p.lease.contractProfit)}</dd>
            <dt>Thu hồi chi phí setup</dt><dd>{p.lease.setupPaybackMonths !== null ? `khoảng ${p.lease.setupPaybackMonths.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tháng` : "không thu hồi được"}</dd>
          </dl><p className="caption">Bài ghi âm nói đơn vị vận hành tốt hòa vốn ở khoảng 1,5–1,6 lần tiền thuê tòa, đơn vị mới vào nghề 1,7–1,8 lần (tham khảo).</p></section>}
          <p className="caption">Chỉ là phép tính trên số bạn nhập, không phải khuyến nghị. Bản nháp được nhớ trên trình duyệt này.</p>
        </>}
      </aside>
    </div>
    {input && p && <Scenarios input={input} base={p} f={f} set={set} />}
    </>
  );
}
