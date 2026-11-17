"use client";
import { Fragment, useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, hanoiDate, parseMoneyInput } from "../lib/format";
import { buildingPlan, measureOf, scenario, sensitivity, type BuildingInput, type BuildingPlan, type Measure } from "./building-calc";
import type { Method } from "./loan-calc";
import { PREFILL_EVENT, type LoanPrefill } from "./loan-tool";

const DRAFT_KEY = "building-tool-draft-v1";
const OCCUPANCIES = [50, 60, 70, 80, 90, 100];
const RENT_PCTS = [-20, -10, 0, 10];
const MEASURES: [Measure, string][] = [["noi", "Lợi nhuận vận hành"], ["buy", "Nếu mua: dòng tiền sau trả nợ"], ["lease", "Nếu thuê lại: lợi nhuận sau tiền thuê tòa"]];
export type Row = { name: string; count: string; price: string; life: string };
type Saved = { id: string; name: string; saved_on: string; method: Method; form: Partial<Record<Key, string>>; rows: Row[] };
const EMPTY = {
  rooms: "", hiMonths: "", hiRent: "", hiOcc: "", loMonths: "", loRent: "", loOcc: "", peakRent: "",
  brokerPct: "", brokerMonths: "", contractMonths: "", otaPct: "", otaShare: "", vatPct: "", pitPct: "", otherPct: "", reservePct: "",
  cleaning: "", common: "", staff: "", internet: "", insurance: "", fixedOther: "", pcccCost: "", pcccYears: "",
  price: "", buyCosts: "", renovation: "", own: "", loanRate: "", termYears: "", holdYears: "", holdRate: "", promoRate: "", promoMonths: "",
  leaseRent: "", deposit: "", setup: "", leaseMonths: "",
  badOcc: "", badRent: "", goodOcc: "", goodRent: "",
};
type Key = keyof typeof EMPTY;
const LABELS: Partial<Record<Key, string>> = {
  rooms: "Số phòng", hiMonths: "Mùa cao điểm (tháng)", hiRent: "Giá mùa cao điểm (đ/phòng/tháng)", hiOcc: "Có khách mùa cao điểm (%)",
  loMonths: "Mùa thấp điểm (tháng)", loRent: "Giá mùa thấp điểm (đ/phòng/tháng)", loOcc: "Có khách mùa thấp điểm (%)", peakRent: "Giá cao nhất môi giới đưa",
  brokerMonths: "Hoa hồng môi giới (tháng tiền thuê/hợp đồng)", contractMonths: "Thời hạn hợp đồng bình quân (tháng)", brokerPct: "Hoa hồng môi giới (%)",
  otaPct: "Hoa hồng OTA (%)", otaShare: "Doanh thu qua OTA (%)", vatPct: "Thuế GTGT (%)", pitPct: "Thuế TNCN (%)", otherPct: "Chi phí khác (%)",
  reservePct: "Dự phòng rủi ro (%)", cleaning: "Vệ sinh (đ/tháng)", common: "Điện nước khu vực chung (đ/tháng)", staff: "Nhân sự (đ/tháng)",
  internet: "Internet, truyền hình (đ/tháng)", insurance: "Bảo hiểm (đ/tháng)", fixedOther: "Cố định khác (đ/tháng)", pcccCost: "Giấy PCCC (đ)",
  pcccYears: "Giấy PCCC dùng trong (năm)", price: "Giá mua (đ)", buyCosts: "Thuế phí sang tên (đ)", renovation: "Sửa sang, nội thất (đ)", own: "Vốn tự có (đ)",
  loanRate: "Lãi vay (%/năm)", termYears: "Thời hạn vay (năm)", holdYears: "Số năm nắm giữ", holdRate: "Lãi tiền gửi để so (%/năm)", promoRate: "Lãi ưu đãi (%/năm)", promoMonths: "Thời gian ưu đãi (tháng)", leaseRent: "Tiền thuê nguyên tòa (đ/tháng)", deposit: "Tiền cọc (đ)",
  setup: "Chi phí setup (đ)", leaseMonths: "Thời hạn hợp đồng thuê tòa (tháng)", badOcc: "Kịch bản xấu: có khách ± (điểm %)",
  badRent: "Kịch bản xấu: giá ± (%)", goodOcc: "Kịch bản tốt: có khách ± (điểm %)", goodRent: "Kịch bản tốt: giá ± (%)",
};
const MONEY = new Set<Key>(["hiRent", "loRent", "peakRent", "cleaning", "common", "staff", "internet", "insurance", "fixedOther", "pcccCost",
  "price", "buyCosts", "renovation", "own", "leaseRent", "deposit", "setup"]);

const SIGNED = new Set<Key>(["badOcc", "badRent", "goodOcc", "goodRent"]);
const signedNum = (s: string) => (s.trim() ? Number(s.trim().replace(/\s/g, "").replace("−", "-").replace(",", ".")) : null);
const money = (s: string) => (s.trim() ? Number(parseMoneyInput(s) ?? NaN) : 0);
const num = (s: string) => (s.trim() ? Number(s.trim().replace(/\./g, "").replace(",", ".")) : 0);
const vnd = (v: number) => formatVnd(String(Math.round(v)));
const pct = (v: number) => formatRatio(v.toFixed(6), 1);

/** Commission as months of rent for each lease (1 month on a 12-month lease = 8,333…%); null when either box is empty. */
export function brokerShare(v: { brokerMonths: number; contractMonths: number }): number | null {
  return v.brokerMonths > 0 && v.contractMonths > 0 ? (v.brokerMonths / v.contractMonths) * 100 : null;
}

/** The boxes as typed → the plan, or what is wrong with them; null until the rooms and a rent are in. */
export function readPlan(f: typeof EMPTY, rows: Row[], method: Method, defaultDepositRate: number | null = null):
  { error: string } | { plan: BuildingPlan; input: BuildingInput } | null {
  const rooms = num(f.rooms);
  if (!rooms || (!f.hiRent.trim() && !f.loRent.trim())) return null;
  const values = Object.fromEntries((Object.keys(EMPTY) as Key[]).filter((k) => !SIGNED.has(k))
    .map((k) => [k, MONEY.has(k) ? money(f[k]) : num(f[k])])) as Record<Key, number>;
  if (Object.values(values).some((v) => Number.isNaN(v) || v < 0)) return { error: "Các ô chỉ nhận số không âm." };
  if (!Number.isInteger(rooms)) return { error: "Số phòng là số nguyên." };
  for (const k of ["hiOcc", "loOcc", "brokerPct", "otaPct", "otaShare", "vatPct", "pitPct", "otherPct", "reservePct"] as Key[])
    if (values[k] > 100) return { error: "Các tỷ lệ % từ 0 đến 100." };
  if (values.brokerMonths > 0 && values.contractMonths > 0 && values.brokerMonths >= values.contractMonths)
    return { error: "Hoa hồng môi giới nhập theo số tháng tiền thuê (ví dụ 1), không phải số tiền; số tháng phải nhỏ hơn thời hạn hợp đồng." };
  const equipment = rows.filter((r) => r.count.trim() || r.price.trim()).map((r) => ({ name: r.name, count: num(r.count), price: money(r.price), lifeYears: num(r.life) }));
  if (equipment.some((e) => Number.isNaN(e.count) || Number.isNaN(e.price) || !e.lifeYears)) return { error: "Mỗi thiết bị cần số lượng, giá và tuổi thọ (năm)." };
  const input: BuildingInput = {
    rooms, peakRent: values.peakRent || null,
    seasons: [{ months: values.hiMonths, rent: values.hiRent, occupancy: values.hiOcc }, { months: values.loMonths, rent: values.loRent, occupancy: values.loOcc }]
      .filter((s) => s.months > 0),
    brokerPct: brokerShare(values) ?? values.brokerPct, otaPct: values.otaPct, otaShare: values.otaShare, vatPct: values.vatPct, pitPct: values.pitPct, otherPct: values.otherPct,
    reservePct: values.reservePct,
    fixed: { cleaning: values.cleaning, common: values.common, staff: values.staff, internet: values.internet, insurance: values.insurance, other: values.fixedOther },
    equipment, pccc: { cost: values.pcccCost, years: values.pcccYears },
    buy: values.price > 0 ? { price: values.price, buyCosts: values.buyCosts, renovation: values.renovation, own: values.own, loanRate: values.loanRate,
      termYears: values.termYears, method, holdYears: values.holdYears || undefined,
      promoRate: (f.promoRate ?? "").trim() ? values.promoRate : undefined, promoMonths: values.promoMonths || undefined,
      depositRate: (f.holdRate ?? "").trim() ? values.holdRate : defaultDepositRate ?? undefined } : undefined,
    lease: values.leaseRent > 0 ? { rent: values.leaseRent, deposit: values.deposit, setup: values.setup, months: values.leaseMonths } : undefined,
  };
  if (!input.seasons.length) return { error: "Nhập số tháng của ít nhất một mùa." };
  const shareOfRevenue = ((100 - input.otaShare) * input.brokerPct + input.otaShare * input.otaPct) / 100 + input.vatPct + input.pitPct + input.otherPct
    + input.reservePct;
  if (shareOfRevenue >= 100) return { error: "Các khoản tính theo % doanh thu cộng lại đã từ 100% trở lên: kiểm tra lại các ô % ở mục 2." };
  if (input.buy && input.buy.own > input.buy.price + input.buy.buyCosts + input.buy.renovation) return { error: "Vốn tự có lớn hơn tổng tiền mua và sửa sang." };
  if (input.buy && input.buy.price + input.buy.buyCosts + input.buy.renovation > input.buy.own && (!input.buy.termYears || !Number.isInteger(input.buy.termYears)))
    return { error: "Có vay thì nhập thời hạn vay (số năm nguyên)." };
  return { plan: buildingPlan(input), input };
}

/** "cao hơn 3,2 điểm %" or "thấp hơn …": a yield against the deposit rate. */
export function gapText(y: number, rate: number): string {
  const d = (y - rate) * 100;
  return `${d >= 0 ? "cao" : "thấp"} hơn ${Math.abs(d).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} điểm %`;
}

/** B7: the owner's named plans (settings/building_plans), saved as typed, reopened, and compared side by side. */
type Store = { data: { version: number; plans: Saved[] } | null; busy: boolean; error: string | null; write: (plans: Saved[]) => Promise<boolean> };

/** The owner's named plans (settings/building_plans): read once, written whole with the version read. */
function useSavedPlans(): Store {
  const [data, setData] = useState<{ version: number; plans: Saved[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<{ version: number; plans: Saved[] }>("settings/building-plans").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const write = async (plans: Saved[]) => {
    if (!data) return false;
    setBusy(true); setError(null);
    try { setData(await api("settings/building-plans", { method: "PUT", body: { plans, expected_version: data.version, request_id: requestId() } })); return true; }
    catch (e) { setError(e instanceof ApiError ? e.failure.message : "Không lưu được."); return false; } finally { setBusy(false); }
  };
  return { data, busy, error, write };
}

/** Lưu right in the result panel: a new plan under a name, or the opened one again ("Lưu thay đổi"). */
function SaveBox({ store, current, hasPlan, initialName, onSaved }: { store: Store; current: { f: typeof EMPTY; rows: Row[]; method: Method }; hasPlan: boolean;
  initialName: string; onSaved: (name: string) => void }) {
  const [name, setName] = useState(initialName);
  const [done, setDone] = useState<string | null>(null);
  const { data, busy, error, write } = store;
  const same = data?.plans.find((x) => x.name === name.trim());
  const save = async () => {
    if (!data || !name.trim()) return;
    const form = Object.fromEntries(Object.entries(current.f).filter(([, v]) => v.trim())) as Partial<Record<Key, string>>;
    const item: Saved = { id: same?.id ?? requestId().slice(0, 24), name: name.trim(), saved_on: hanoiDate(), method: current.method, form,
      rows: current.rows.filter((r) => r.count.trim() || r.price.trim() || r.name.trim()) };
    if (await write([...data.plans.filter((x) => x.id !== item.id), item])) {
      setDone(`Đã lưu "${item.name}" lúc ${new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}.`);
      onSaved(item.name);
    }
  };
  return (
    <form className="bt-save" aria-label="Lưu phương án" onSubmit={(e) => { e.preventDefault(); void save(); }}>
      <label className="field">Tên phương án<input aria-label="Tên phương án" maxLength={60} value={name} onChange={(e) => { setName(e.target.value); setDone(null); }}
        placeholder="ví dụ Tòa 10 phòng gần biển" /></label>
      <button type="submit" className="btn primary" disabled={busy || !data || !name.trim() || !hasPlan}>{same ? "Lưu thay đổi" : "Lưu phương án"}</button>
      {same && !done && <span className="caption">Đã có phương án tên này: lưu sẽ thay số cũ.</span>}
      {!hasPlan && <span className="caption">Nhập đủ số phòng và giá thuê để lưu.</span>}
      {done && <span className="caption" role="status">{done}</span>}
      {error && <span className="errors" role="alert">{error}</span>}
    </form>
  );
}

/** Each saved plan's monthly results by model (operating, buying after the loan, leasing after the rent), and the range holding them and zero. */
export function compareBars(items: { name: string; plan: BuildingPlan | null }[]) {
  const groups = items.map(({ name, plan }) => ({ name, bars: plan ? ([["noi", plan.noiMonth], ["buy", plan.buy?.cashMonth ?? null],
    ["lease", plan.lease?.profitMonth ?? null]] as [Measure, number | null][]).filter((b): b is [Measure, number] => b[1] !== null)
    .map(([id, value]) => ({ id, value })) : [] }));
  const all = groups.flatMap((g) => g.bars.map((b) => b.value)).concat(0);
  return { groups, lo: Math.min(...all), hi: Math.max(...all) };
}

const BAR_CLASS: Record<Measure, string> = { noi: "bt-line-noi", buy: "bt-line-buy", lease: "bt-line-lease" };

/** The saved plans side by side: one group a plan, one bar a model, losses to the left of zero. */
function CompareChart({ items }: { items: { name: string; plan: BuildingPlan | null }[] }) {
  const { groups, lo, hi } = compareBars(items);
  const W = 640, L = 150, R = 90, BAR = 12, GAP = 3, PAD = 10;
  const heights = groups.map((g) => Math.max(g.bars.length, 1) * (BAR + GAP) + PAD);
  const H = heights.reduce((s, h) => s + h, 0) + 18;
  const span = hi - lo || 1;
  const x = (v: number) => L + ((v - lo) / span) * (W - L - R);
  const short = (v: number) => `${v < 0 ? "−" : ""}${Math.abs(v / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tr`;
  const tops = heights.map((_, i) => 4 + heights.slice(0, i).reduce((s, h) => s + h, 0));
  return (
    <figure className="bt-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="So sánh lợi nhuận mỗi tháng của các phương án">
        <line x1={x(0)} x2={x(0)} y1={0} y2={H - 14} className="bt-zero" />
        <text x={x(0)} y={H - 2} textAnchor="middle" className="bt-axis">0</text>
        {groups.map((g, i) => { const y0 = tops[i]; return <g key={g.name}>
          <text x={L - 8} y={y0 + BAR} textAnchor="end" className="bt-axis bt-name">{g.name.length > 24 ? `${g.name.slice(0, 23)}…` : g.name}</text>
          {g.bars.length ? g.bars.map((b, j) => { const y = y0 + j * (BAR + GAP), a = x(Math.min(0, b.value)), w = Math.abs(x(b.value) - x(0));
            return <g key={b.id}><rect x={a} y={y} width={Math.max(w, 1)} height={BAR} className={`bt-bar ${BAR_CLASS[b.id]}`} />
              <text x={b.value < 0 ? a - 4 : a + w + 4} y={y + BAR - 2} textAnchor={b.value < 0 ? "end" : "start"} className="bt-axis">{short(b.value)}</text></g>; })
            : <text x={x(0) + 6} y={y0 + BAR} className="bt-axis">chưa đủ số để tính</text>}
        </g>; })}
      </svg>
      <figcaption className="bt-legend">{(["noi", "buy", "lease"] as Measure[]).map((m) => <span key={m}><i className={`bt-key ${BAR_CLASS[m]}`} />{LINE[m][0]}</span>)}</figcaption>
    </figure>
  );
}

/** The saved plans compared side by side, each to reopen or delete. */
function SavedPlans({ store, open, depositRate }: { store: Store; open: (s: Saved) => void; depositRate: number | null }) {
  const { data, busy, write } = store;
  const rowsOf = data?.plans.map((s) => ({ s, out: readPlan({ ...EMPTY, ...s.form }, s.rows, s.method, depositRate === null ? null : depositRate * 100) })) ?? [];
  const money2 = (v: number | null | undefined) => (v === null || v === undefined ? "—" : <span className={v < 0 ? "negative" : undefined}>{vnd(v)}</span>);
  return (
    <section className="surface" aria-label="Các phương án đã lưu">
      <h2>Các phương án đã lưu</h2>
      <p className="caption">Lưu bằng nút trong khung Kết quả; mở lại và so các tòa cạnh nhau ở đây (tối đa 20). Lưu trong thiết lập cá nhân trên máy, không gửi đi đâu.</p>
      {data && rowsOf.length > 0 && <><h3>Lợi nhuận mỗi tháng của các tòa</h3>
        <CompareChart items={rowsOf.map(({ s, out }) => ({ name: s.name, plan: out && "plan" in out ? out.plan : null }))} /></>}
      {data && (rowsOf.length ? <div className="tablewrap"><table className="fv-table cc-table" aria-label="So sánh các phương án">
        <thead><tr><th>Phương án</th><th className="num">Doanh thu/tháng</th><th className="num">Chi phí % doanh thu</th><th className="num">Lợi nhuận vận hành/tháng</th>
          <th className="num">Mua: dòng tiền/tháng</th><th className="num">Mua: sau ưu đãi/tháng</th><th className="num">Mua: lợi suất vốn tự có</th>
          <th className="num">Mua: giá cần tăng/năm</th><th className="num">Thuê lại: lợi nhuận/tháng</th>
          <th className="num">Thuê lại: có khách tối thiểu</th><th /></tr></thead>
        <tbody>{rowsOf.map(({ s, out }) => { const pl = out && "plan" in out ? out.plan : null; return <tr key={s.id}>
          <td><strong>{s.name}</strong><div className="caption">lưu {s.saved_on.split("-").reverse().join("/")}</div></td>
          {pl ? <>
            <td className="num">{vnd(pl.revenueMonth)}</td><td className="num">{pct(pl.costShare)}</td><td className="num">{money2(pl.noiMonth)}</td>
            <td className="num">{money2(pl.buy?.cashMonth)}</td><td className="num">{money2(pl.buy?.afterOffer?.cashMonth)}</td>
            <td className="num">{pl.buy?.cashOnCash != null ? pct(pl.buy.cashOnCash) : "—"}</td>
            <td className="num">{pl.buy?.hold ? (pl.buy.hold.neededGrowth === null ? "không cần" : `${pct(pl.buy.hold.neededGrowth)} (${pl.buy.hold.years} năm)`) : "—"}</td>
            <td className="num">{money2(pl.lease?.profitMonth)}</td>
            <td className="num">{pl.lease && Number.isFinite(pl.lease.breakevenOccupancy) ? pct(pl.lease.breakevenOccupancy) : "—"}</td>
          </> : <td colSpan={9} className="muted">{out && "error" in out ? out.error : "chưa đủ số để tính"}</td>}
          <td><div className="ib-actions"><button type="button" className="btn" onClick={() => open(s)}>Mở</button>
            <button type="button" className="btn text" aria-label={`Xóa phương án ${s.name}`} disabled={busy}
              onClick={() => { if (window.confirm(`Xóa phương án "${s.name}"?`)) void write(data.plans.filter((x) => x.id !== s.id)); }}>Xóa</button></div></td>
        </tr>; })}</tbody></table></div>
        : <p className="muted">Chưa lưu phương án nào.</p>)}
    </section>
  );
}

/** The yearly price change holding needs to match the deposit; a fall means the rent alone already beats it. */
export function growthText(g: number | null): string {
  if (g === null) return "không cần giá trị còn lại (dòng tiền đã bù đủ)";
  if (g < 0) return `không cần tăng: giá có thể giảm đến ${pct(-g)} một năm mà vẫn bằng gửi tiết kiệm`;
  return `${pct(g)} một năm`;
}

/** Opens the building's purchase loan in the Khoản vay tab, its figures filled in. */
function openLoan(p: LoanPrefill) {
  window.dispatchEvent(new CustomEvent<LoanPrefill>(PREFILL_EVENT, { detail: p }));
  window.history.replaceState(null, "", "/loan?tab=khoan-vay");
  window.scrollTo({ top: 0 });
}

/** What the recording of 17/11/2026 (căn hộ dịch vụ Đà Nẵng, a personal account) says for each line; "Bài không nêu số" where it gave none. */
export const ARTICLE_HINTS: Partial<Record<Key, string>> = {
  peakRent: "Bài: môi giới hay lấy giá ngày cao điểm nhân cả năm",
  hiOcc: "Bài không nêu số",
  loOcc: "Bài: trống phòng mùa thấp điểm mất 15–20% doanh thu (tòa vận hành tốt khoảng 10%)",
  brokerPct: "Bài: 8,3–10% (môi giới cá nhân, mạng xã hội); 8,3% là 1 tháng tiền thuê cho hợp đồng 12 tháng",
  brokerMonths: "Ví dụ 1 tháng tiền thuê mỗi lần môi giới tìm được khách",
  contractMonths: "Bài: khách nước ngoài thường thuê 3–6 tháng",
  otaPct: "Bài: khoảng 15%",
  otaShare: "Bài không nêu số",
  vatPct: "Bài: 5%",
  pitPct: "Bài: 2–5% (tùy cho thuê ngắn hạn hay dài hạn)",
  otherPct: "Bài không nêu số",
  reservePct: "Bài không nêu số (rủi ro phạt khi khách không khai báo tạm trú)",
  cleaning: "Bài: 2.000.000 đ/lần, 1 lần/tuần ≈ 8.000.000 đ/tháng",
  common: "Bài không nêu số (thang máy, đèn hành lang, máy bơm, sảnh)",
  staff: "Bài không nêu số",
  internet: "Bài không nêu số",
  insurance: "Bài không nêu số",
  fixedOther: "Bài không nêu số",
  pcccCost: "Bài không nêu số (bên thuê tự làm, không được hoàn khi trả nhà)",
  leaseRent: "Bài: hòa vốn ở 1,5–1,6 lần tiền thuê nếu vận hành tốt, 1,7–1,8 lần nếu mới vào nghề",
};
/** Only the figures the recording gives as one value; a range (8,3–10%, 2–5%) is left for the owner to choose within. */
const ARTICLE_FILL: Partial<Record<Key, string>> = { otaPct: "15", vatPct: "5", cleaning: "8.000.000" };
const ARTICLE_EQUIPMENT = ["Đèn chiếu sáng", "Thiết bị vệ sinh (bồn cầu, vòi)", "Bình nóng lạnh", "Điều hòa"];

/** The single figures into the boxes still empty, and the equipment the recording names (without numbers) after any already typed. */
export function fillFromArticle<F extends Record<string, string>>(f: F, rows: Row[]): { f: F; rows: Row[] } {
  const filled = { ...f };
  for (const [k, v] of Object.entries(ARTICLE_FILL)) if (k in filled && !filled[k].trim()) (filled as Record<string, string>)[k] = v!;
  const kept = rows.filter((r) => r.name.trim() || r.count.trim() || r.price.trim() || r.life.trim());
  const have = new Set(kept.map((r) => r.name.trim()));
  return { f: filled, rows: [...kept, ...ARTICLE_EQUIPMENT.filter((n) => !have.has(n)).map((name) => ({ name, count: "", price: "", life: "" }))] };
}

function Field({ k, label, f, set, hint }: { k: Key; label: string; f: typeof EMPTY; set: (k: Key, v: string) => void; hint?: string }) {
  const note = ARTICLE_HINTS[k];
  return <label className="field">{label}<input aria-label={label} inputMode={MONEY.has(k) ? "numeric" : "decimal"} value={f[k]} placeholder={hint}
    onChange={(e) => set(k, MONEY.has(k) ? groupDigitsInput(e.target.value) : e.target.value)} />
    {note && <span className="caption bt-hint">{note}</span>}</label>;
}

/** "vận hành 41,2% · mua tòa 63,0% · thuê lại 58,4%"; a model that cannot break even even full says so. */
export function breakevenText(p: BuildingPlan): string {
  const one = (v: number) => (Number.isFinite(v) && v <= 1 ? pct(v) : "kín phòng cũng chưa hòa vốn");
  return [`vận hành ${one(p.breakevenOccupancy)}`, ...(p.buy ? [`mua tòa (sau trả nợ) ${one(p.buy.breakevenOccupancy)}`] : []),
    ...(p.lease ? [`thuê lại (sau tiền thuê tòa) ${one(p.lease.breakevenOccupancy)}`] : [])].join(" · ");
}

/** Shown only when printed: the plan's name, the day, and the figures it was worked out from. */
function PrintHead({ name, f, rows }: { name: string | null; f: typeof EMPTY; rows: Row[] }) {
  const shown = (Object.keys(LABELS) as Key[]).filter((k) => f[k].trim());
  const kit = rows.filter((r) => r.name.trim() || r.count.trim());
  const items: [string, string][] = [...shown.map((k) => [LABELS[k]!, f[k]] as [string, string]),
    ...kit.map((r) => [`Thiết bị: ${r.name || "—"}`, [r.count && `${r.count} cái`, r.price && `${r.price} đ`, r.life && `${r.life} năm`].filter(Boolean).join(" · ")] as [string, string])];
  const pairs = (list: [string, string][]) => list.reduce<[string, string][][]>((out, x, i) => (i % 3 ? out[out.length - 1].push(x) : out.push([x]), out), []);
  return (
    <section className="print-only bt-print" aria-label="Bản in phương án">
      <h2>{name ?? "Phương án chưa lưu"}</h2>
      <p className="caption">In ngày {hanoiDate().split("-").reverse().join("/")} · phép tính trên số đã nhập, không phải khuyến nghị.</p>
      <table className="fv-table" aria-label="Số đầu vào"><tbody>{pairs(items).map((two, i) => <tr key={i}>{two.map(([label, value]) =>
        <Fragment key={label}><td>{label}</td><td className="num">{value}</td></Fragment>)}</tr>)}</tbody></table>
    </section>
  );
}

export const OCC_STEPS = Array.from({ length: 21 }, (_, i) => i * 5);
const LINE: Record<Measure, [string, string]> = { noi: ["Vận hành", "bt-line-noi"], buy: ["Mua tòa (sau trả nợ)", "bt-line-buy"],
  lease: ["Thuê lại (sau tiền thuê tòa)", "bt-line-lease"] };

/** Each model's monthly result from empty to full rooms (rents as entered), its breakeven occupancy, and the range that fits them and zero. */
export function chartLines(input: BuildingInput, base: BuildingPlan) {
  const series = (["noi", "buy", "lease"] as Measure[]).filter((m) => measureOf(base, m) !== null).map((m) => ({
    id: m, label: LINE[m][0], cls: LINE[m][1], values: sensitivity(input, OCC_STEPS, [0], m).map((row) => row[0] as number),
    breakeven: m === "noi" ? base.breakevenOccupancy : m === "buy" ? base.buy!.breakevenOccupancy : base.lease!.breakevenOccupancy }));
  const all = series.flatMap((s) => s.values).concat(0);
  return { series, lo: Math.min(...all), hi: Math.max(...all) };
}

/** Lợi nhuận theo tỷ lệ có khách: one line a model, zero marked, each breakeven point dotted. */
function ProfitChart({ input, base }: { input: BuildingInput; base: BuildingPlan }) {
  const { series, lo, hi } = chartLines(input, base);
  const W = 640, H = 200, L = 70, B = 22, span = hi - lo || 1;
  const x = (occ: number) => L + (occ / 100) * (W - L - 8);
  const y = (v: number) => 8 + (1 - (v - lo) / span) * (H - B - 8);
  const short = (v: number) => `${(v / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 0 })} tr`;
  return (
    <figure className="bt-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Lợi nhuận mỗi tháng theo tỷ lệ có khách">
        {[0, 25, 50, 75, 100].map((o) => <g key={o}><line x1={x(o)} x2={x(o)} y1={8} y2={H - B} className="bt-grid" />
          <text x={x(o)} y={H - 6} textAnchor="middle" className="bt-axis">{o}%</text></g>)}
        <line x1={L} x2={W - 8} y1={y(0)} y2={y(0)} className="bt-zero" />
        <text x={L - 6} y={y(hi) + 4} textAnchor="end" className="bt-axis">{short(hi)}</text>
        <text x={L - 6} y={y(0) + 4} textAnchor="end" className="bt-axis">0</text>
        <text x={L - 6} y={y(lo) + 4} textAnchor="end" className="bt-axis">{short(lo)}</text>
        {series.map((s) => <g key={s.id}>
          <polyline points={s.values.map((v, i) => `${x(OCC_STEPS[i])},${y(v)}`).join(" ")} className={`bt-line ${s.cls}`} />
          {Number.isFinite(s.breakeven) && s.breakeven <= 1 && <circle cx={x(s.breakeven * 100)} cy={y(0)} r={4} className={`bt-dot ${s.cls}`} />}
        </g>)}
      </svg>
      <figcaption className="bt-legend">{series.map((s) => <span key={s.id}><i className={`bt-key ${s.cls}`} />{s.label}
        {Number.isFinite(s.breakeven) && s.breakeven <= 1 ? ` (hòa vốn ${pct(s.breakeven)})` : " (kín phòng cũng chưa hòa vốn)"}</span>)}</figcaption>
    </figure>
  );
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
      <p data-testid="breakeven"><strong>Tỷ lệ có khách hòa vốn</strong> (áp cho cả năm, giá như đã nhập): {breakevenText(base)}</p>
      <h3>Lợi nhuận mỗi tháng theo tỷ lệ có khách (giá như đã nhập)</h3>
      <ProfitChart input={input} base={base} />
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
  const store = useSavedPlans();
  const [opened, setOpened] = useState<string | null>(null);
  const [openCount, setOpenCount] = useState(0);  // the save box starts afresh, with the plan's name, each time a plan is opened
  const [depositRate, setDepositRate] = useState<number | null>(null);
  useEffect(() => {
    api<{ default_rate: string | null }>("passive-income").then((v) => setDepositRate(v.default_rate ? Number(v.default_rate) / 100 : null), () => undefined);
  }, []);
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

  const out = readPlan(f, rows, method, depositRate === null ? null : depositRate * 100);  // light arithmetic: worked out on each render
  const p = out && "plan" in out ? out.plan : null;
  const input = out && "input" in out ? out.input : null;
  const F = (k: Key, label: string, hint?: string) => <Field k={k} label={label} f={f} set={set} hint={hint} />;
  return (
    <>
    <PrintHead name={opened} f={f} rows={rows} />
    <div className="bt">
      <div className="bt-inputs">
        <div className="notice bt-article">
          <p>Gợi ý dưới mỗi ô lấy từ bài ghi âm ngày 17/11/2026 về căn hộ dịch vụ cao cấp ở Đà Nẵng (chia sẻ cá nhân, không phải số liệu thống kê). Bài ước tổng
            chi phí bán phòng và thuế 22–25%, tổng chi phí vận hành 33–43% doanh thu.</p>
          <button type="button" className="btn" onClick={() => { const out = fillFromArticle(f, rows); setF(out.f); setRows(out.rows); }}>
            Điền gợi ý từ bài vào ô còn trống</button>
          <p className="caption">Chỉ điền những số bài nêu một giá trị (hoa hồng OTA 15%, thuế GTGT 5%, vệ sinh 8.000.000 đ/tháng) và tên các thiết bị bài nhắc;
            dòng bài nêu khoảng (môi giới 8,3–10%, TNCN 2–5%) bạn tự chọn. Không đè số bạn đã nhập.</p>
        </div>
        <section className="surface" aria-label="Doanh thu theo mùa">
          <h2>1. Doanh thu theo mùa</h2>
          <p className="caption">Giá thuê một phòng mỗi tháng và tỷ lệ phòng có khách trong từng mùa. Hai mùa cộng lại nên đủ 12 tháng.</p>
          <div className="formgrid">{F("rooms", "Số phòng")}{F("peakRent", "Giá cao nhất môi giới đưa (đ/phòng/tháng)", "để so")}</div>
          <div className="formgrid">{F("hiMonths", "Mùa cao điểm: số tháng")}{F("hiRent", "Giá (đ/phòng/tháng)")}{F("hiOcc", "Có khách (%)")}</div>
          <div className="formgrid">{F("loMonths", "Mùa thấp điểm: số tháng")}{F("loRent", "Giá thấp điểm (đ/phòng/tháng)")}{F("loOcc", "Có khách thấp điểm (%)")}</div>
        </section>
        <section className="surface" aria-label="Chi phí theo doanh thu">
          <h2>2. Chi phí tính theo % doanh thu</h2>
          <div className="formgrid">{F("brokerMonths", "Hoa hồng môi giới: số tháng tiền thuê mỗi hợp đồng", "ví dụ 1")}{F("contractMonths", "Thời hạn hợp đồng bình quân (tháng)")}
            {F("brokerPct", "Hoa hồng môi giới, mạng xã hội (%)")}</div>
          {(() => {
            const share = brokerShare({ brokerMonths: num(f.brokerMonths), contractMonths: num(f.contractMonths) });
            return share !== null && Number.isFinite(share) && share < 100 ? <p className="caption" data-testid="broker-share">Hoa hồng môi giới tính theo hợp đồng: {f.brokerMonths} tháng tiền thuê
              / hợp đồng {f.contractMonths} tháng = {share.toLocaleString("vi-VN", { maximumFractionDigits: 3 })}% doanh thu mỗi tháng (dùng số này thay ô %).</p>
              : <p className="caption">Nhập số tháng tiền thuê và thời hạn hợp đồng để tính hoa hồng đúng theo hợp đồng; hoặc nhập thẳng % ở ô bên cạnh.</p>;
          })()}
          <div className="formgrid">{F("otaPct", "Hoa hồng OTA (%)")}{F("otaShare", "Phần doanh thu qua OTA (%)")}</div>
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
          <div className="formgrid">{F("holdYears", "Số năm nắm giữ (để so với gửi tiết kiệm)")}
            {F("holdRate", "Lãi tiền gửi để so (%/năm)", depositRate !== null ? `để trống: ${(depositRate * 100).toLocaleString("vi-VN", { maximumFractionDigits: 2 })}` : undefined)}</div>
          <div className="formgrid">{F("promoRate", "Lãi ưu đãi (%/năm)", "nếu có")}{F("promoMonths", "Thời gian ưu đãi (tháng)", "ví dụ 12")}</div>
          {(f.promoRate ?? "").trim() && <p className="caption">Có ưu đãi: ô &ldquo;Lãi vay&rdquo; dưới đây là lãi sau khi hết ưu đãi.</p>}
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
        <div className="bt-result-head"><h2>Kết quả</h2>
          {p && <button type="button" className="btn" onClick={() => window.print()}>In bản 1 trang</button>}</div>
        <SaveBox key={openCount} store={store} current={{ f, rows, method }} hasPlan={!!p} initialName={opened ?? ""} onSaved={setOpened} />
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
            {p.buy.loan > 0 && <><dt>Trả ngân hàng mỗi tháng (bình quân năm đầu)</dt><dd>{vnd(p.buy.loanPaymentMonth)}
              {input?.buy && <div><button type="button" className="btn text" onClick={() => openLoan({ principal: p.buy!.loan, rate: input.buy!.loanRate, promoRate: input.buy!.promoRate, promoMonths: input.buy!.promoMonths,
                years: input.buy!.termYears, method: input.buy!.method, note: `Đang xem khoản vay mua tòa ${opened ? `"${opened}"` : "đang tính"} (vay ${vnd(p.buy!.loan)}, ${input.buy!.loanRate
                .toLocaleString("vi-VN")}%/năm, ${input.buy!.termYears} năm). Thay đổi ở đây không đổi số ở tab Tòa nhà.` })}>Xem lịch trả nợ chi tiết</button></div>}</dd></>}
            {p.buy.afterOffer && <>
              <dt>Sau ưu đãi (từ tháng {p.buy.afterOffer.month}): trả ngân hàng mỗi tháng</dt><dd>{vnd(p.buy.afterOffer.payment)}</dd>
              <dt>Sau ưu đãi: dòng tiền còn lại mỗi tháng</dt><dd><strong className={p.buy.afterOffer.cashMonth < 0 ? "negative" : undefined}>{vnd(p.buy.afterOffer.cashMonth)}</strong></dd>
              <dt>Sau ưu đãi: tỷ lệ có khách tối thiểu để không âm tiền</dt><dd>{Number.isFinite(p.buy.afterOffer.breakevenOccupancy) && p.buy.afterOffer.breakevenOccupancy <= 1
                ? pct(p.buy.afterOffer.breakevenOccupancy) : "kín phòng cũng chưa đủ"}</dd>
            </>}
            <dt>Dòng tiền còn lại mỗi tháng</dt><dd><strong className={p.buy.cashMonth < 0 ? "negative" : undefined}>{vnd(p.buy.cashMonth)}</strong></dd>
            <dt>Lợi suất ròng trên tổng tiền bỏ ra</dt><dd>{pct(p.buy.netYield)} một năm</dd>
            {p.buy.cashOnCash !== null && <><dt>Lợi suất trên vốn tự có</dt><dd>{pct(p.buy.cashOnCash)} một năm</dd></>}
            {p.buy.cashOnCash !== null && depositRate !== null && <><dt>So với gửi tiết kiệm 12 tháng ({pct(depositRate)})</dt>
              <dd className={p.buy.cashOnCash < depositRate ? "negative" : undefined}>{gapText(p.buy.cashOnCash, depositRate)}</dd></>}
            {p.buy.hold && <>
              <dt>Nếu giữ vốn tự có ở tiền gửi {p.buy.hold.years} năm</dt><dd>{vnd(p.buy.hold.keep)}</dd>
              <dt>Giá tòa cần đạt sau {p.buy.hold.years} năm để bằng gửi tiết kiệm</dt><dd><strong>{vnd(p.buy.hold.neededPrice)}</strong></dd>
              <dt>Giá tòa cần tăng mỗi năm</dt><dd className={p.buy.hold.neededGrowth !== null && p.buy.hold.neededGrowth > 0 ? "negative" : undefined}>
                {growthText(p.buy.hold.neededGrowth)}</dd>
            </>}
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
            {(() => {
              const capital = (input?.lease?.setup ?? 0) + (input?.lease?.deposit ?? 0);
              if (!capital) return null;
              const y = (p.lease.profitMonth * 12) / capital;
              return <><dt>Lợi nhuận một năm trên tiền bỏ ra (setup + cọc)</dt><dd>{pct(y)}</dd>
                {depositRate !== null && <><dt>So với gửi tiết kiệm 12 tháng ({pct(depositRate)})</dt>
                  <dd className={y < depositRate ? "negative" : undefined}>{gapText(y, depositRate)}</dd></>}</>;
            })()}
            <dt>Thu hồi chi phí setup</dt><dd>{p.lease.setupPaybackMonths !== null ? `khoảng ${p.lease.setupPaybackMonths.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tháng` : "không thu hồi được"}</dd>
          </dl><p className="caption">Bài ghi âm nói đơn vị vận hành tốt hòa vốn ở khoảng 1,5–1,6 lần tiền thuê tòa, đơn vị mới vào nghề 1,7–1,8 lần (tham khảo).</p></section>}
          <p className="caption">Chỉ là phép tính trên số bạn nhập, không phải khuyến nghị. Bản nháp được nhớ trên trình duyệt này.</p>
        </>}
      </aside>
    </div>
    {input && p && <Scenarios input={input} base={p} f={f} set={set} />}
    <SavedPlans store={store} depositRate={depositRate} open={(s) => { setF({ ...EMPTY, ...s.form }); setRows(s.rows.length ? s.rows : [{ name: "", count: "", price: "", life: "" }]);
      setMethod(s.method); setOpened(s.name); setOpenCount((n) => n + 1); window.scrollTo({ top: 0 }); }} />
    </>
  );
}
