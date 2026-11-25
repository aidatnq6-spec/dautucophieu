"use client";
import { useEffect, useState } from "react";
import { CalendarClock, Check, Pencil, Plus, Trash2 } from "lucide-react";
import { ApiError, api } from "../lib/api";

type Figures = { period: string; cip: string | null; ppe_gross: string | null } | null;
type Project = { id: string; name: string; due: string; read_period: string | null; cip_value: string | null; budget: string | null; source_url: string | null;
  note: string; status: "open" | "done"; done_on: string | null; postpones: { from: string; to: string; on: string; reason: string }[];
  state: "upcoming" | "waiting_report" | "due" | "done"; at_read: Figures; at_due: Figures; latest: Figures };
type Ranges = { period: string | null; groups: Record<string, { from: number; to: number }> };
type Prepaid = { year: string; items: Record<string, string>; total: string; summed: boolean; prepaid_lt: string | null; years_left: string | null; to_pbt: string | null };
type Deal = { id: string; name: string; date: string; share: string; price: string; net_assets: string; years: number | null; source_url: string | null; note: string;
  goodwill: string; kind: "goodwill" | "bargain" | "none"; per_year: string | null; ends: string | null; charging: boolean; gain_year: string | null;
  computed: string; note_goodwill: string | null; gap: string | null; nci_part: string | null };
type Move = { year: string; opening: string; added: string; amortised: string | null; closing: string; decline: string; other: string | null; to_admin: string | null; to_pbt: string | null };
type Bargain = { year: string; gain: string; deals: string[]; pbt: string | null; share: string | null; pbt_without: string | null; flag: boolean | null };
type Data = { symbol: string; version: number; projects: Project[]; ranges: Ranges; groups: Record<string, string>; prepaid: Prepaid[]; prepaid_kinds: Record<string, string>;
  deals: Deal[]; goodwill_amort: Record<string, string>; goodwill_moves: Move[]; bargains: Bargain[];
  loans: Loan[]; debt_notes: { period?: string; current_portion?: string; fx_shock?: string }; debt: Debt; currencies: string[]; terms: Record<string, string>;
  segments: SegmentPeriod[] };
type SegmentRow = { name: string; revenue: string; cogs: string; gross: string; margin: string | null; share: string | null };
type SegmentPeriod = { period: string; rows: SegmentRow[]; revenue: string; cogs: string; gross: string; margin: string | null; reported_revenue: string | null;
  reported_cogs: string | null; revenue_gap: string | null; cogs_gap: string | null };
type Loan = { id: string; lender: string; currency: string; term: "short" | "long"; balance: string; rate_from: string | null; rate_to: string | null; base: string | null;
  margin: string | null; maturity: string | null; collateral: string; note: string };
type Debt = { period: string | null; total: string; by_currency: Record<string, string>; by_term: Record<string, string>; maturities: Record<string, string>;
  rates: Record<string, { from: string | null; to: string | null; floating: string[] }>; reported: string | null; covered: string | null;
  current_portion: string | null; fx_shock: string | null; foreign: string; fx_loss: string | null; fx_to_pbt: string | null };
type LoanDraft = { id?: string; lender: string; currency: string; term: string; balance: string; rate_from: string; rate_to: string; base: string; margin: string;
  maturity: string; collateral: string; note: string };
type DealDraft = { id?: string; name: string; date: string; share: string; price: string; net_assets: string; years: string; source_url: string; note: string;
  note_goodwill: string; nci_part: string };
type Draft = { id?: string; name: string; due: string; read_period: string; cip_value: string; budget: string; source_url: string; note: string };

const requestId = () => `fan-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const ty = (v: string | null) => (v === null ? "—" : Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 1 }));
const bn = (v: string | null) => (v === null ? "chưa có" : `${Math.round(Number(v) / 1e9).toLocaleString("vi-VN")} tỷ`);
const day = (iso: string) => iso.split("-").reverse().join("/");

/** 2027-Q3 → Q3/2027, as the owner types it. */
export function quarterInput(q: string): string {
  return `Q${q.slice(-1)}/${q.slice(0, 4)}`;
}

const periodInput = (p: string | null) => (p === null ? "" : p.length === 4 ? p : quarterInput(p));

export function stateText(p: Pick<Project, "state" | "due" | "done_on"> & { postpones: unknown[] }): string {
  const base = p.state === "done" ? `Đã hoàn thành${p.done_on ? ` (xác nhận ${day(p.done_on)})` : ""}`
    : p.state === "due" ? "Đến hạn: xác nhận đã hoàn thành hoặc lùi hạn"
      : p.state === "waiting_report" ? `Chờ báo cáo ${quarterInput(p.due)}` : `Đang làm, dự kiến xong ${quarterInput(p.due)}`;
  return p.postpones.length ? `${base} · đã lùi ${p.postpones.length} lần` : base;
}

/** Long-term prepaid expenses over the year's allocation, true only at that pace. */
export function yearsLeftText(r: Pick<Prepaid, "year" | "years_left">): string {
  return r.years_left === null ? "—" : `≈ ${Number(r.years_left).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} năm nếu giữ nhịp phân bổ năm ${r.year}`;
}

const num = (v: string) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 1 });

/** What the deal's goodwill does to profit: a yearly charge until it ends, or a one-off gain for a bargain purchase. */
export function dealText(d: Pick<Deal, "kind" | "goodwill" | "per_year" | "ends" | "gain_year">): string {
  if (d.kind === "bargain") return `Lãi mua rẻ ${num(d.goodwill.replace("-", ""))} tỷ: lợi nhuận một lần năm ${d.gain_year}, loại ra khi so lợi nhuận các năm`;
  if (d.kind === "none") return "Giá mua bằng phần tài sản thuần: không có lợi thế thương mại";
  return d.per_year && d.ends ? `Lợi thế thương mại ${num(d.goodwill)} tỷ, phân bổ ${num(d.per_year)} tỷ/năm vào chi phí đến ${day(d.ends)}`
    : `Lợi thế thương mại ${num(d.goodwill)} tỷ; ghi số năm phân bổ để thấy mức trừ vào lợi nhuận mỗi năm`;
}

const signed = (v: string) => (Number(v) < 0 ? `−${num(v.replace("-", ""))}` : num(v));
const pct = (v: string) => `${(Number(v) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`;

/** The formula's goodwill beside the notes', when the owner wrote the notes' figure. */
export function gapText(d: Pick<Deal, "computed" | "note_goodwill" | "gap">): string | null {
  return d.note_goodwill === null || d.gap === null ? null
    : `Công thức: ${signed(d.computed)} tỷ; thuyết minh: ${signed(d.note_goodwill)} tỷ (lệch ${signed(d.gap)} tỷ, dùng số thuyết minh)`;
}

/** A year's bargain gains: no cash came with them; profit before tax with and without them. */
export function bargainText(b: Pick<Bargain, "year" | "gain" | "pbt" | "share" | "pbt_without">): string {
  const head = `Năm ${b.year}: lãi mua rẻ ${num(b.gain)} tỷ (không có tiền đi kèm)`;
  if (b.pbt === null) return `${head}; chưa có LNTT năm này trong báo cáo đã lưu`;
  const weight = b.share === null ? `; doanh nghiệp lỗ trước thuế ${signed(b.pbt)} tỷ` : `, bằng ${pct(b.share)} LNTT ${num(b.pbt)} tỷ`;
  return `${head}${weight}; LNTT loại lãi mua rẻ ${signed(b.pbt_without ?? "0")} tỷ`;
}

/** The owner's loans against the borrowings on the balance sheet at the period read. */
export function coverText(d: Pick<Debt, "period" | "total" | "reported" | "covered">): string {
  const head = `Các khoản bạn ghi: ${num(d.total)} tỷ`;
  return d.reported === null || d.covered === null || d.period === null ? `${head}; ghi kỳ báo cáo đã đọc để đối chiếu với bảng cân đối`
    : `${head}, bằng ${pct(d.covered)} vay ngắn hạn + dài hạn trên bảng cân đối ${periodInput(d.period)} (${num(d.reported)} tỷ)`;
}

/** The exchange scenario: the foreign-currency balance × the owner's fall of the đồng. */
export function fxText(d: Pick<Debt, "foreign" | "fx_shock" | "fx_loss" | "fx_to_pbt">): string {
  if (Number(d.foreign) === 0) return "Không có dư nợ ngoại tệ trong các khoản bạn ghi";
  if (d.fx_shock === null || d.fx_loss === null) return "Ghi mức mất giá giả định để xem kịch bản tỷ giá";
  return `Kịch bản (không phải dự báo): đồng Việt Nam mất giá ${num(d.fx_shock)}% thì dư nợ ngoại tệ ${num(d.foreign)} tỷ tăng thêm khoảng ${num(d.fx_loss)} tỷ`
    + (d.fx_to_pbt === null ? "" : `, bằng ${pct(d.fx_to_pbt)} LNTT kỳ đã đọc`);
}

const rateText = (l: Pick<Loan, "rate_from" | "rate_to" | "base" | "margin">) => {
  const fixed = l.rate_from && l.rate_to ? (l.rate_from === l.rate_to ? `${num(l.rate_from)}%` : `${num(l.rate_from)}–${num(l.rate_to)}%`)
    : l.rate_from ? `từ ${num(l.rate_from)}%` : l.rate_to ? `đến ${num(l.rate_to)}%` : "";
  const floating = l.base || l.margin ? `${l.base ?? "thả nổi"}${l.margin ? ` + ${num(l.margin)}%` : ""}` : "";
  return [fixed, floating].filter(Boolean).join("; ") || "—";
};

/** The segments' totals against the stored net revenue and cost of sales of the period. */
export function segmentCheckText(v: Pick<SegmentPeriod, "period" | "revenue" | "cogs" | "reported_revenue" | "reported_cogs" | "revenue_gap" | "cogs_gap">): string {
  if (v.revenue_gap === null || v.cogs_gap === null) return "Chưa có số của kỳ này trong báo cáo đã lưu để đối chiếu";
  if (Number(v.revenue_gap) === 0 && Number(v.cogs_gap) === 0) return `Tổng các mảng khớp doanh thu thuần và giá vốn của báo cáo ${periodInput(v.period)}`;
  const plus = (x: string) => (Number(x) > 0 ? `+${num(x)}` : signed(x));
  return `Tổng các mảng lệch báo cáo ${periodInput(v.period)}: doanh thu ${plus(v.revenue_gap)} tỷ${Number(v.revenue_gap) > 0 ? " (có thể chưa trừ các khoản giảm trừ)" : ""}, giá vốn ${plus(v.cogs_gap)} tỷ`;
}

const loanRaw = (l: LoanDraft | Loan) => ({ ...(l.id ? { id: l.id } : {}), lender: l.lender, currency: l.currency, term: l.term, balance: l.balance,
  rate_from: l.rate_from ?? "", rate_to: l.rate_to ?? "", base: l.base ?? "", margin: l.margin ?? "", maturity: l.maturity ?? "", collateral: l.collateral, note: l.note });
const loanDraft = (l: Loan): LoanDraft => ({ id: l.id, lender: l.lender, currency: l.currency, term: l.term, balance: l.balance, rate_from: l.rate_from ?? "",
  rate_to: l.rate_to ?? "", base: l.base ?? "", margin: l.margin ?? "", maturity: l.maturity ?? "", collateral: l.collateral, note: l.note });

const dealRaw = (d: DealDraft | Deal) => ({ ...(d.id ? { id: d.id } : {}), name: d.name, date: d.date, share: d.share, price: d.price, net_assets: d.net_assets,
  years: d.years === null ? "" : String(d.years), source_url: d.source_url || null, note: d.note, note_goodwill: d.note_goodwill ?? "", nci_part: d.nci_part ?? "" });

const fig = (f: Figures) => (f ? `${periodInput(f.period)}: XDCB ${bn(f.cip)}, nguyên giá ${bn(f.ppe_gross)}` : null);

function toRaw(d: Draft) {
  return { ...(d.id ? { id: d.id } : {}), name: d.name, due: d.due, read_period: d.read_period || null, cip_value: d.cip_value || null, budget: d.budget || null,
    source_url: d.source_url || null, note: d.note };
}

function fromProject(p: Project): Draft {
  return { id: p.id, name: p.name, due: quarterInput(p.due), read_period: periodInput(p.read_period), cip_value: p.cip_value ?? "", budget: p.budget ?? "",
    source_url: p.source_url ?? "", note: p.note };
}

const blank = (): Draft => ({ name: "", due: "", read_period: "", cip_value: "", budget: "", source_url: "", note: "" });

export function FixedAssetNotes({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Data | null>(null);
  const [hidden, setHidden] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [ranges, setRanges] = useState<Record<string, { from: string; to: string }> | null>(null);
  const [rangePeriod, setRangePeriod] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [allocation, setAllocation] = useState<{ old?: string; year: string; values: Record<string, string> } | null>(null);
  const [deal, setDeal] = useState<DealDraft | null>(null);
  const [loan, setLoan] = useState<LoanDraft | null>(null);
  const [debtNotes, setDebtNotes] = useState<{ period: string; current_portion: string; fx_shock: string } | null>(null);
  const [segment, setSegment] = useState<{ old?: string; period: string; rows: { name: string; revenue: string; cogs: string }[] } | null>(null);
  const base = `stock/${encodeURIComponent(symbol)}/fixed-asset-notes`;
  useEffect(() => {
    api<Data>(base).then(setData, (e) => {
      if (e instanceof ApiError && e.failure.code === "not_a_company") setHidden(true); else setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
    });
  }, [base]);
  if (hidden || (!data && !message)) return null;
  async function send(path: string, method: "PUT" | "POST", body: Record<string, unknown>) {
    if (!data) return;
    try {
      setData(await api<Data>(path, { method, body: { ...body, expected_version: data.version, request_id: requestId() } }));
      setDraft(null);
      setRanges(null);
      setAllocation(null);
      setDeal(null);
      setLoan(null);
      setDebtNotes(null);
      setSegment(null);
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const rangesRaw = (groups: Record<string, { from: string | number; to: string | number }>, period: string | null) => ({ ...groups, period });
  const keptRanges = () => rangesRaw(data?.ranges.groups ?? {}, data?.ranges.period ?? null);
  const others = (id?: string) => (data?.projects ?? []).filter((p) => p.id !== id).map((p) => toRaw(fromProject(p)));
  const saveProjects = (projects: ReturnType<typeof toRaw>[]) => send(base, "PUT", { projects, ranges: keptRanges() });
  const keptPrepaid = (skip?: string) => Object.fromEntries((data?.prepaid ?? []).filter((r) => r.year !== skip)
    .map((r) => [r.year, { ...r.items, ...(r.summed ? {} : { total: r.total }) }]));
  const otherDeals = (id?: string) => (data?.deals ?? []).filter((d) => d.id !== id).map(dealRaw);
  const saveDeals = (deals: ReturnType<typeof dealRaw>[]) => send(base, "PUT", { projects: others(), ranges: keptRanges(), deals });
  const charging = (data?.deals ?? []).filter((d) => d.charging && d.per_year).reduce((s, d) => s + Number(d.per_year), 0);
  const savePrepaid = (prepaid: Record<string, Record<string, string>>) => send(base, "PUT", { projects: others(), ranges: keptRanges(), prepaid });
  const otherLoans = (id?: string) => (data?.loans ?? []).filter((l) => l.id !== id).map(loanRaw);
  const saveLoans = (loans: ReturnType<typeof loanRaw>[]) => send(base, "PUT", { projects: others(), ranges: keptRanges(), loans });
  const keptSegments = (skip?: string) => Object.fromEntries((data?.segments ?? []).filter((s) => s.period !== skip)
    .map((s) => [periodInput(s.period), s.rows.map((r) => ({ name: r.name, revenue: r.revenue, cogs: r.cogs }))]));
  const saveSegments = (segments: Record<string, { name: string; revenue: string; cogs: string }[]>) =>
    send(base, "PUT", { projects: others(), ranges: keptRanges(), segments });
  function amortise(year: string, current: string | null) {
    const value = window.prompt(`Phân bổ lợi thế thương mại năm ${year} theo thuyết minh (tỷ đồng; để trống để xóa):`, current ?? "");
    if (value === null || !data) return;
    const next = { ...data.goodwill_amort };
    if (value.trim()) next[year] = value.trim(); else delete next[year];
    void send(base, "PUT", { projects: others(), ranges: keptRanges(), goodwill_amort: next });
  }
  function later(p: Project) {
    const to = window.prompt(`Quý hoàn thành mới cho ${p.name} (dạng Q2/2027):`);
    if (!to) return;
    const reason = window.prompt("Lý do lùi hạn (có thể để trống):") ?? "";
    void send(`${base}/postpone`, "POST", { id: p.id, to: to.trim(), reason });
  }
  return (
    <section className="surface" aria-label="Thuyết minh TSCĐ (nhập tay)">
      <h2>Thuyết minh TSCĐ (nhập tay)</h2>
      {message && <p className="errors" role="alert">{message}</p>}
      <h3>Dự án XDCB</h3>
      {data && data.projects.length > 0 ? <table className="fv-table" aria-label={`Dự án XDCB ${symbol}`}>
        <thead><tr><th>Dự án</th><th>Tình trạng</th><th className="num">XDCB bạn ghi (tỷ)</th><th className="num">Tổng vốn dự kiến (tỷ)</th><th>Số của cả công ty</th><th></th></tr></thead>
        <tbody>{data.projects.map((p) => <tr key={p.id} data-testid="fan-project">
          <td data-label="Dự án">{p.source_url ? <a href={p.source_url} target="_blank" rel="noreferrer noopener">{p.name}</a> : p.name}
            {p.note && <div className="caption">{p.note}</div>}
            {p.postpones.length > 0 && <div className="caption">{p.postpones.map((x) => `${day(x.on)}: ${quarterInput(x.from)} → ${quarterInput(x.to)}${x.reason ? ` (${x.reason})` : ""}`).join(" · ")}</div>}</td>
          <td data-label="Tình trạng" className={p.state === "due" ? "negative" : ""}>{stateText(p)}</td>
          <td className="num" data-label="XDCB bạn ghi">{ty(p.cip_value)}{p.read_period && <div className="caption">{periodInput(p.read_period)}</div>}</td>
          <td className="num" data-label="Tổng vốn dự kiến">{ty(p.budget)}</td>
          <td data-label="Số của cả công ty"><div className="caption">{[fig(p.at_read), fig(p.at_due), p.latest && p.latest.period !== p.at_due?.period ? fig(p.latest) : null].filter(Boolean).join(" · ") || "—"}</div></td>
          <td className="actions">
            <button type="button" className="btn" aria-label={`Sửa ${p.name}`} onClick={() => setDraft(fromProject(p))}><Pencil size={14} aria-hidden="true" />Sửa</button>
            {p.status === "open" && <>
              <button type="button" className="btn" aria-label={`Lùi hạn ${p.name}`} onClick={() => later(p)}><CalendarClock size={14} aria-hidden="true" />Lùi hạn</button>
              <button type="button" className="btn" aria-label={`Đã hoàn thành ${p.name}`} onClick={() => { if (window.confirm(`Ghi ${p.name} là đã hoàn thành?`)) void send(`${base}/complete`, "POST", { id: p.id }); }}>
                <Check size={14} aria-hidden="true" />Đã hoàn thành</button></>}
            <button type="button" className="btn" aria-label={`Xóa ${p.name}`} onClick={() => { if (window.confirm(`Xóa dự án ${p.name}?`)) void saveProjects(others(p.id)); }}>
              <Trash2 size={14} aria-hidden="true" />Xóa</button></td>
        </tr>)}</tbody>
      </table> : data && <p className="muted">Chưa có dự án nào. Ghi các dự án trong thuyết minh chi phí xây dựng cơ bản dở dang của báo cáo tài chính.</p>}
      {!draft && data && <button type="button" className="btn" onClick={() => setDraft(blank())}><Plus size={15} aria-hidden="true" />Thêm dự án</button>}
      {draft && <form className="pp-form" aria-label="Dự án XDCB" onSubmit={(e) => { e.preventDefault(); void saveProjects([...others(draft.id), toRaw(draft)]); }}>
        <label className="field">Tên dự án<input value={draft.name} maxLength={120} required onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></label>
        <label className="field">Quý hoàn thành dự kiến<input value={draft.due} placeholder="Q3/2027" required disabled={Boolean(draft.id)}
          onChange={(e) => setDraft({ ...draft, due: e.target.value })} />{draft.id && <span className="caption">Đổi bằng nút Lùi hạn.</span>}</label>
        <label className="field">Kỳ báo cáo đã đọc<input value={draft.read_period} placeholder="2025 hoặc Q2/2026" onChange={(e) => setDraft({ ...draft, read_period: e.target.value })} /></label>
        <label className="field">Giá trị trong XDCB tại kỳ đó (tỷ đồng)<input inputMode="decimal" value={draft.cip_value} onChange={(e) => setDraft({ ...draft, cip_value: e.target.value })} /></label>
        <label className="field">Tổng vốn đầu tư dự kiến (tỷ đồng)<input inputMode="decimal" value={draft.budget} onChange={(e) => setDraft({ ...draft, budget: e.target.value })} /></label>
        <label className="field">Link tài liệu nguồn<input type="url" value={draft.source_url} onChange={(e) => setDraft({ ...draft, source_url: e.target.value })} placeholder="https://…" /></label>
        <label className="field">Ghi chú<input value={draft.note} maxLength={500} onChange={(e) => setDraft({ ...draft, note: e.target.value })} /></label>
        <div className="row"><button className="btn primary" type="submit">Lưu dự án</button><button className="btn" type="button" onClick={() => setDraft(null)}>Hủy</button></div>
      </form>}
      <h3>Khung khấu hao</h3>
      {data && !ranges && <>
        {Object.keys(data.ranges.groups).length > 0 ? <table className="fv-table" aria-label={`Khung khấu hao ${symbol}`}>
          <thead><tr><th>Nhóm tài sản</th><th className="num">Số năm</th></tr></thead>
          <tbody>{Object.entries(data.ranges.groups).map(([k, r]) => <tr key={k}><td>{data.groups[k] ?? k}</td><td className="num">{r.from === r.to ? r.from : `${r.from}–${r.to}`}</td></tr>)}</tbody>
        </table> : <p className="muted">Chưa ghi khung khấu hao.</p>}
        {data.ranges.period && <p className="caption">Theo báo cáo {periodInput(data.ranges.period)}.</p>}
        <button type="button" className="btn" onClick={() => {
          setRanges(Object.fromEntries(Object.keys(data.groups).map((k) => [k, { from: String(data.ranges.groups[k]?.from ?? ""), to: String(data.ranges.groups[k]?.to ?? "") }])));
          setRangePeriod(periodInput(data.ranges.period));
        }}><Pencil size={14} aria-hidden="true" />Sửa khung khấu hao</button>
      </>}
      {data && ranges && <form className="pp-form" aria-label="Khung khấu hao" onSubmit={(e) => {
        e.preventDefault();
        const filled = Object.fromEntries(Object.entries(ranges).filter(([, r]) => r.from.trim() && r.to.trim()));
        void send(base, "PUT", { projects: others(), ranges: rangesRaw(filled, rangePeriod.trim() || null) });
      }}>
        {Object.entries(data.groups).map(([k, label]) => <div key={k} className="row">
          <span className="field">{label}</span>
          <label className="field">Từ (năm)<input inputMode="numeric" value={ranges[k].from} onChange={(e) => setRanges({ ...ranges, [k]: { ...ranges[k], from: e.target.value } })} /></label>
          <label className="field">Đến (năm)<input inputMode="numeric" value={ranges[k].to} onChange={(e) => setRanges({ ...ranges, [k]: { ...ranges[k], to: e.target.value } })} /></label>
        </div>)}
        <label className="field">Kỳ báo cáo đã đọc<input value={rangePeriod} placeholder="2025" onChange={(e) => setRangePeriod(e.target.value)} /></label>
        <div className="row"><button className="btn primary" type="submit">Lưu khung khấu hao</button><button className="btn" type="button" onClick={() => setRanges(null)}>Hủy</button></div>
      </form>}
      <h3>Chi phí trả trước: phân bổ trong năm</h3>
      {data && data.prepaid.length > 0 ? <table className="fv-table" aria-label={`Phân bổ chi phí trả trước ${symbol}`}>
        <thead><tr><th>Năm</th>{Object.entries(data.prepaid_kinds).map(([k, label]) => <th key={k} className="num">{label}</th>)}<th className="num">Tổng phân bổ (tỷ)</th>
          <th className="num">CPTT dài hạn cuối năm</th><th>Số năm phân bổ còn lại</th><th className="num">Phân bổ ÷ LNTT</th><th></th></tr></thead>
        <tbody>{data.prepaid.map((r) => <tr key={r.year} data-testid="fan-prepaid">
          <td data-label="Năm">{r.year}</td>
          {Object.keys(data.prepaid_kinds).map((k) => <td key={k} className="num" data-label={data.prepaid_kinds[k]}>{ty(r.items[k] ?? null)}</td>)}
          <td className="num" data-label="Tổng phân bổ">{ty(r.total)}{r.summed && <div className="caption">cộng các loại đã nhập</div>}</td>
          <td className="num" data-label="CPTT dài hạn cuối năm">{r.prepaid_lt === null ? "chưa có" : bn(r.prepaid_lt)}</td>
          <td data-label="Số năm phân bổ còn lại">{yearsLeftText(r)}</td>
          <td className="num" data-label="Phân bổ ÷ LNTT">{r.to_pbt === null ? "—" : `${(Number(r.to_pbt) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`}</td>
          <td className="actions">
            <button type="button" className="btn" aria-label={`Sửa phân bổ ${r.year}`} onClick={() => setAllocation({ old: r.year, year: r.year,
              values: { ...r.items, ...(r.summed ? {} : { total: r.total }) } })}><Pencil size={14} aria-hidden="true" />Sửa</button>
            <button type="button" className="btn" aria-label={`Xóa phân bổ ${r.year}`} onClick={() => { if (window.confirm(`Xóa phân bổ năm ${r.year}?`)) void savePrepaid(keptPrepaid(r.year)); }}>
              <Trash2 size={14} aria-hidden="true" />Xóa</button></td>
        </tr>)}</tbody>
      </table> : data && <p className="muted">Chưa ghi số phân bổ. Lấy từ thuyết minh chi phí trả trước (phần &quot;phân bổ trong năm&quot;).</p>}
      {data && !allocation && <button type="button" className="btn" onClick={() => setAllocation({ year: String(new Date().getFullYear() - 1), values: {} })}>
        <Plus size={15} aria-hidden="true" />Thêm năm phân bổ</button>}
      {data && allocation && <form className="pp-form" aria-label="Phân bổ chi phí trả trước" onSubmit={(e) => {
        e.preventDefault();
        const values = Object.fromEntries(Object.entries(allocation.values).filter(([, v]) => v.trim()));
        void savePrepaid({ ...keptPrepaid(allocation.old), [allocation.year.trim()]: values });
      }}>
        <label className="field">Năm<input inputMode="numeric" maxLength={4} value={allocation.year} required onChange={(e) => setAllocation({ ...allocation, year: e.target.value })} /></label>
        {[...Object.entries(data.prepaid_kinds), ["total", "Tổng phân bổ (nếu thuyết minh ghi)"]].map(([k, label]) =>
          <label key={k} className="field">{label} (tỷ đồng)<input inputMode="decimal" value={allocation.values[k] ?? ""}
            onChange={(e) => setAllocation({ ...allocation, values: { ...allocation.values, [k]: e.target.value } })} /></label>)}
        <div className="row"><button className="btn primary" type="submit">Lưu phân bổ</button><button className="btn" type="button" onClick={() => setAllocation(null)}>Hủy</button></div>
      </form>}
      <p className="caption">Số năm phân bổ còn lại = chi phí trả trước dài hạn cuối năm (báo cáo đã lưu) ÷ tổng phân bổ năm đó, chỉ đúng nếu doanh nghiệp giữ nhịp phân bổ
        như năm đó. Phần phân bổ là chi phí ghi vào lợi nhuận mà không tốn thêm tiền (tiền đã chi từ trước). Không ghi tổng thì phần mềm cộng các loại bạn đã nhập.</p>
      <h3>Thương vụ mua bán, sáp nhập</h3>
      {data && data.deals.length > 0 ? <>
        <table className="fv-table" aria-label={`Thương vụ mua bán ${symbol}`}>
          <thead><tr><th>Công ty được mua</th><th>Ngày mua</th><th className="num">Tỷ lệ mua</th><th className="num">Giá mua (tỷ)</th><th className="num">Tài sản thuần hợp lý (tỷ)</th>
            <th>Lợi thế thương mại</th><th></th></tr></thead>
          <tbody>{data.deals.map((d) => <tr key={d.id} data-testid="fan-deal">
            <td data-label="Công ty được mua">{d.source_url ? <a href={d.source_url} target="_blank" rel="noreferrer noopener">{d.name}</a> : d.name}
              {d.note && <div className="caption">{d.note}</div>}</td>
            <td data-label="Ngày mua">{day(d.date)}</td>
            <td className="num" data-label="Tỷ lệ mua">{num(d.share)}%</td>
            <td className="num" data-label="Giá mua">{num(d.price)}</td>
            <td className="num" data-label="Tài sản thuần hợp lý">{num(d.net_assets)}</td>
            <td data-label="Lợi thế thương mại" className={d.kind === "bargain" ? "negative" : ""}>{dealText(d)}
              {gapText(d) && <div className="caption">{gapText(d)}</div>}
              {d.nci_part && <div className="caption">Phần của cổ đông không kiểm soát: {num(d.nci_part)} tỷ</div>}</td>
            <td className="actions">
              <button type="button" className="btn" aria-label={`Sửa thương vụ ${d.name}`} onClick={() => setDeal({ ...dealRaw(d), date: day(d.date), source_url: d.source_url ?? "" })}>
                <Pencil size={14} aria-hidden="true" />Sửa</button>
              <button type="button" className="btn" aria-label={`Xóa thương vụ ${d.name}`} onClick={() => { if (window.confirm(`Xóa thương vụ ${d.name}?`)) void saveDeals(otherDeals(d.id)); }}>
                <Trash2 size={14} aria-hidden="true" />Xóa</button></td>
          </tr>)}</tbody>
        </table>
        {charging > 0 && <p className="caption" data-testid="fan-charging">Các thương vụ đang phân bổ trừ vào lợi nhuận khoảng {num(String(charging))} tỷ mỗi năm (theo số năm bạn ghi).</p>}
      </> : data && <p className="muted">Chưa ghi thương vụ nào. Lấy từ thuyết minh hợp nhất kinh doanh (mua công ty con) của báo cáo tài chính.</p>}
      {data && !deal && <button type="button" className="btn" onClick={() => setDeal({ name: "", date: "", share: "", price: "", net_assets: "", years: "", source_url: "", note: "",
        note_goodwill: "", nci_part: "" })}>
        <Plus size={15} aria-hidden="true" />Thêm thương vụ</button>}
      {data && deal && <form className="pp-form" aria-label="Thương vụ mua bán" onSubmit={(e) => { e.preventDefault(); void saveDeals([...otherDeals(deal.id), dealRaw(deal)]); }}>
        <label className="field">Công ty được mua<input value={deal.name} maxLength={120} required onChange={(e) => setDeal({ ...deal, name: e.target.value })} /></label>
        <label className="field">Ngày mua<input value={deal.date} placeholder="15/03/2024" required onChange={(e) => setDeal({ ...deal, date: e.target.value })} /></label>
        <label className="field">Tỷ lệ mua (%)<input inputMode="decimal" value={deal.share} required onChange={(e) => setDeal({ ...deal, share: e.target.value })} /></label>
        <label className="field">Giá mua (tỷ đồng)<input inputMode="decimal" value={deal.price} required onChange={(e) => setDeal({ ...deal, price: e.target.value })} /></label>
        <label className="field">Giá trị hợp lý tài sản thuần của công ty được mua (tỷ đồng, cả công ty)<input inputMode="decimal" value={deal.net_assets} required
          onChange={(e) => setDeal({ ...deal, net_assets: e.target.value })} /></label>
        <label className="field">Số năm phân bổ (tối đa 10)<input inputMode="numeric" value={deal.years} onChange={(e) => setDeal({ ...deal, years: e.target.value })} /></label>
        <label className="field">Lợi thế thương mại theo thuyết minh (tỷ đồng, âm nếu mua rẻ; tùy chọn)<input inputMode="decimal" value={deal.note_goodwill}
          onChange={(e) => setDeal({ ...deal, note_goodwill: e.target.value })} /></label>
        <label className="field">Phần của cổ đông không kiểm soát (tỷ đồng, tùy chọn)<input inputMode="decimal" value={deal.nci_part}
          onChange={(e) => setDeal({ ...deal, nci_part: e.target.value })} /></label>
        <label className="field">Link tài liệu nguồn<input type="url" value={deal.source_url} onChange={(e) => setDeal({ ...deal, source_url: e.target.value })} placeholder="https://…" /></label>
        <label className="field">Ghi chú<input value={deal.note} maxLength={500} onChange={(e) => setDeal({ ...deal, note: e.target.value })} /></label>
        <div className="row"><button className="btn primary" type="submit">Lưu thương vụ</button><button className="btn" type="button" onClick={() => setDeal(null)}>Hủy</button></div>
      </form>}
      <p className="caption">Lợi thế thương mại = giá mua − tỷ lệ mua × giá trị hợp lý tài sản thuần của công ty được mua. Dương: ghi thành tài sản, phân bổ đều vào chi phí trong số năm
        bạn ghi (VAS tối đa 10 năm). Âm: giao dịch mua rẻ, ghi ngay vào lợi nhuận năm mua, là lợi nhuận một lần. Số do bạn nhập từ thuyết minh; phần mềm chỉ tính theo công thức.
        Ghi số thuyết minh thì phần mềm dùng số đó và hiện phần lệch so với công thức.</p>
      <h3>Các khoản vay</h3>
      {data && data.loans.length > 0 ? <>
        <table className="fv-table" aria-label={`Các khoản vay ${symbol}`}>
          <thead><tr><th>Bên cho vay</th><th>Loại tiền</th><th>Kỳ hạn</th><th className="num">Dư nợ (tỷ)</th><th>Lãi suất</th><th>Đáo hạn</th><th>Tài sản đảm bảo</th><th></th></tr></thead>
          <tbody>{data.loans.map((l) => <tr key={l.id} data-testid="fan-loan">
            <td data-label="Bên cho vay">{l.lender}{l.note && <div className="caption">{l.note}</div>}</td>
            <td data-label="Loại tiền">{l.currency}</td><td data-label="Kỳ hạn">{data.terms[l.term]}</td>
            <td className="num" data-label="Dư nợ">{num(l.balance)}</td><td data-label="Lãi suất">{rateText(l)}</td>
            <td data-label="Đáo hạn">{l.maturity ?? "—"}</td><td data-label="Tài sản đảm bảo">{l.collateral || "—"}</td>
            <td className="actions">
              <button type="button" className="btn" aria-label={`Sửa khoản vay ${l.lender}`} onClick={() => setLoan(loanDraft(l))}><Pencil size={14} aria-hidden="true" />Sửa</button>
              <button type="button" className="btn" aria-label={`Xóa khoản vay ${l.lender}`} onClick={() => { if (window.confirm(`Xóa khoản vay ${l.lender}?`)) void saveLoans(otherLoans(l.id)); }}>
                <Trash2 size={14} aria-hidden="true" />Xóa</button></td>
          </tr>)}</tbody>
        </table>
        <ul className="quality-list" data-testid="fan-debt">
          <li>{coverText(data.debt)}</li>
          <li>Theo loại tiền: {Object.entries(data.debt.by_currency).map(([c, v]) => `${c} ${num(v)} tỷ`).join(" · ")}; theo kỳ hạn: {Object.entries(data.debt.by_term)
            .map(([t, v]) => `${data.terms[t] ?? t} ${num(v)} tỷ`).join(" · ")}</li>
          <li>Lãi suất theo loại tiền: {Object.entries(data.debt.rates).map(([c, r]) => `${c} ${r.from && r.to ? `${num(r.from)}–${num(r.to)}%` : "chưa ghi"}${r.floating.length
            ? `, thả nổi ${r.floating.join(", ")}` : ""}`).join(" · ")}</li>
          <li>Đáo hạn: {Object.entries(data.debt.maturities).map(([y, v]) => `${y === "none" ? "chưa ghi năm" : y} ${num(v)} tỷ`).join(" · ")}
            {data.debt.current_portion && ` · nợ dài hạn đến hạn trả trong 12 tháng ${num(data.debt.current_portion)} tỷ`}</li>
          <li>{fxText(data.debt)}</li>
        </ul>
      </> : data && <p className="muted">Chưa ghi khoản vay nào. Lấy từ thuyết minh vay ngắn hạn, dài hạn của báo cáo tài chính.</p>}
      {data && !loan && <button type="button" className="btn" onClick={() => setLoan({ lender: "", currency: "VND", term: "short", balance: "", rate_from: "", rate_to: "", base: "",
        margin: "", maturity: "", collateral: "", note: "" })}><Plus size={15} aria-hidden="true" />Thêm khoản vay</button>}
      {data && !debtNotes && <button type="button" className="btn" onClick={() => setDebtNotes({ period: periodInput(data.debt_notes.period ?? null),
        current_portion: data.debt_notes.current_portion ?? "", fx_shock: data.debt_notes.fx_shock ?? "" })}><Pencil size={14} aria-hidden="true" />Kỳ đã đọc, nợ đến hạn, kịch bản tỷ giá</button>}
      {data && loan && <form className="pp-form" aria-label="Khoản vay" onSubmit={(e) => { e.preventDefault(); void saveLoans([...otherLoans(loan.id), loanRaw(loan)]); }}>
        <label className="field">Bên cho vay<input value={loan.lender} maxLength={120} required onChange={(e) => setLoan({ ...loan, lender: e.target.value })} /></label>
        <label className="field">Loại tiền<select value={loan.currency} onChange={(e) => setLoan({ ...loan, currency: e.target.value })}>
          {data.currencies.map((c) => <option key={c} value={c}>{c}</option>)}</select></label>
        <label className="field">Kỳ hạn<select value={loan.term} onChange={(e) => setLoan({ ...loan, term: e.target.value })}>
          {Object.entries(data.terms).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label className="field">Dư nợ (tỷ đồng, quy đổi theo thuyết minh)<input inputMode="decimal" value={loan.balance} required onChange={(e) => setLoan({ ...loan, balance: e.target.value })} /></label>
        <label className="field">Lãi suất từ (%/năm)<input inputMode="decimal" value={loan.rate_from} onChange={(e) => setLoan({ ...loan, rate_from: e.target.value })} /></label>
        <label className="field">Lãi suất đến (%/năm)<input inputMode="decimal" value={loan.rate_to} onChange={(e) => setLoan({ ...loan, rate_to: e.target.value })} /></label>
        <label className="field">Lãi suất cơ sở nếu thả nổi<input value={loan.base} maxLength={30} placeholder="Libor, SOFR…" onChange={(e) => setLoan({ ...loan, base: e.target.value })} /></label>
        <label className="field">Biên độ (%/năm)<input inputMode="decimal" value={loan.margin} onChange={(e) => setLoan({ ...loan, margin: e.target.value })} /></label>
        <label className="field">Năm đáo hạn<input inputMode="numeric" maxLength={4} value={loan.maturity} onChange={(e) => setLoan({ ...loan, maturity: e.target.value })} /></label>
        <label className="field">Tài sản đảm bảo<input value={loan.collateral} maxLength={300} onChange={(e) => setLoan({ ...loan, collateral: e.target.value })} /></label>
        <label className="field">Ghi chú<input value={loan.note} maxLength={500} onChange={(e) => setLoan({ ...loan, note: e.target.value })} /></label>
        <div className="row"><button className="btn primary" type="submit">Lưu khoản vay</button><button className="btn" type="button" onClick={() => setLoan(null)}>Hủy</button></div>
      </form>}
      {data && debtNotes && <form className="pp-form" aria-label="Ghi chú nợ vay" onSubmit={(e) => {
        e.preventDefault(); void send(base, "PUT", { projects: others(), ranges: keptRanges(), debt_notes: debtNotes }); }}>
        <label className="field">Kỳ báo cáo đã đọc<input value={debtNotes.period} placeholder="2021 hoặc Q2/2026" onChange={(e) => setDebtNotes({ ...debtNotes, period: e.target.value })} /></label>
        <label className="field">Nợ dài hạn đến hạn trả trong 12 tháng (tỷ đồng)<input inputMode="decimal" value={debtNotes.current_portion}
          onChange={(e) => setDebtNotes({ ...debtNotes, current_portion: e.target.value })} /></label>
        <label className="field">Giả định đồng Việt Nam mất giá (%)<input inputMode="decimal" value={debtNotes.fx_shock} onChange={(e) => setDebtNotes({ ...debtNotes, fx_shock: e.target.value })} /></label>
        <div className="row"><button className="btn primary" type="submit">Lưu</button><button className="btn" type="button" onClick={() => setDebtNotes(null)}>Hủy</button></div>
      </form>}
      <p className="caption">Ghi các khoản vay từ thuyết minh (ngân hàng, loại tiền, kỳ hạn, lãi suất, đáo hạn, tài sản đảm bảo); VNDirect chỉ có tổng vay ngắn hạn và dài hạn. Lãi suất hiện
        theo khoảng, không lấy trung bình. Kịch bản tỷ giá là mức mất giá bạn tự giả định, không phải dự báo; lỗ tỷ giá thực tế còn tùy cách doanh nghiệp phòng ngừa.</p>
      <h3>Doanh thu, giá vốn theo mảng</h3>
      {data && data.segments.length > 0 ? data.segments.map((s) => <div key={s.period} data-testid="fan-segments">
        <table className="fv-table" aria-label={`Doanh thu theo mảng ${symbol} ${periodInput(s.period)}`}>
          <caption>{periodInput(s.period)}</caption>
          <thead><tr><th>Mảng</th><th className="num">Doanh thu (tỷ)</th><th className="num">Giá vốn (tỷ)</th><th className="num">Lãi gộp (tỷ)</th><th className="num">Biên gộp</th>
            <th className="num">Đóng góp lãi gộp</th></tr></thead>
          <tbody>{s.rows.map((r) => <tr key={r.name}><td data-label="Mảng">{r.name}</td><td className="num" data-label="Doanh thu">{num(r.revenue)}</td>
            <td className="num" data-label="Giá vốn">{num(r.cogs)}</td><td className={`num${Number(r.gross) < 0 ? " negative" : ""}`} data-label="Lãi gộp">{signed(r.gross)}</td>
            <td className="num" data-label="Biên gộp">{r.margin === null ? "—" : pct(r.margin)}</td>
            <td className="num" data-label="Đóng góp lãi gộp">{r.share === null ? "—" : pct(r.share)}</td></tr>)}
            <tr><td><strong>Tổng</strong></td><td className="num">{num(s.revenue)}</td><td className="num">{num(s.cogs)}</td><td className="num">{signed(s.gross)}</td>
              <td className="num">{s.margin === null ? "—" : pct(s.margin)}</td><td className="num">100,0%</td></tr></tbody>
        </table>
        <p className="caption">{segmentCheckText(s)}</p>
        <div className="row">
          <button type="button" className="btn" aria-label={`Sửa mảng ${periodInput(s.period)}`} onClick={() => setSegment({ old: periodInput(s.period), period: periodInput(s.period),
            rows: s.rows.map((r) => ({ name: r.name, revenue: r.revenue, cogs: r.cogs })) })}><Pencil size={14} aria-hidden="true" />Sửa</button>
          <button type="button" className="btn" aria-label={`Xóa mảng ${periodInput(s.period)}`} onClick={() => {
            if (window.confirm(`Xóa các mảng kỳ ${periodInput(s.period)}?`)) void saveSegments(keptSegments(s.period)); }}><Trash2 size={14} aria-hidden="true" />Xóa</button>
        </div>
      </div>) : data && <p className="muted">Chưa ghi mảng nào. Lấy từ thuyết minh doanh thu và giá vốn hàng bán của báo cáo tài chính.</p>}
      {data && !segment && <button type="button" className="btn" onClick={() => setSegment({ period: String(new Date().getFullYear() - 1),
        rows: [{ name: "", revenue: "", cogs: "" }] })}><Plus size={15} aria-hidden="true" />Thêm kỳ theo mảng</button>}
      {data && segment && <form className="pp-form" aria-label="Doanh thu theo mảng" onSubmit={(e) => {
        e.preventDefault();
        const rows = segment.rows.filter((r) => r.name.trim() || r.revenue.trim() || r.cogs.trim());
        void saveSegments({ ...Object.fromEntries(Object.entries(keptSegments()).filter(([p]) => p !== segment.old)), [segment.period.trim()]: rows });
      }}>
        <label className="field">Kỳ báo cáo<input value={segment.period} placeholder="2021 hoặc Q2/2026" required onChange={(e) => setSegment({ ...segment, period: e.target.value })} /></label>
        {segment.rows.map((r, i) => <div key={i} className="row">
          <label className="field">Mảng {i + 1}<input value={r.name} maxLength={120} onChange={(e) => setSegment({ ...segment, rows: segment.rows.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)) })} /></label>
          <label className="field">Doanh thu (tỷ)<input inputMode="decimal" value={r.revenue} onChange={(e) => setSegment({ ...segment, rows: segment.rows.map((x, j) => (j === i ? { ...x, revenue: e.target.value } : x)) })} /></label>
          <label className="field">Giá vốn (tỷ)<input inputMode="decimal" value={r.cogs} onChange={(e) => setSegment({ ...segment, rows: segment.rows.map((x, j) => (j === i ? { ...x, cogs: e.target.value } : x)) })} /></label>
        </div>)}
        <button type="button" className="btn" onClick={() => setSegment({ ...segment, rows: [...segment.rows, { name: "", revenue: "", cogs: "" }] })}><Plus size={15} aria-hidden="true" />Thêm mảng</button>
        <div className="row"><button className="btn primary" type="submit">Lưu các mảng</button><button className="btn" type="button" onClick={() => setSegment(null)}>Hủy</button></div>
      </form>}
      <p className="caption">Ghi doanh thu và giá vốn từng mảng từ thuyết minh (VNDirect chỉ có tổng). Phần mềm tính lãi gộp, biên gộp, % đóng góp vào tổng lãi gộp và đối chiếu tổng
        với doanh thu thuần, giá vốn của báo cáo đã lưu; thuyết minh thường ghi doanh thu trước giảm trừ nên tổng có thể lệch phần giảm trừ.</p>
      {data && data.bargains.length > 0 && <>
        <h3>Lợi nhuận có lãi mua rẻ</h3>
        <ul className="quality-list">{data.bargains.map((b) => <li key={b.year} data-testid="fan-bargain">
          {b.flag && <><span className="pill warn">cần xem kỹ</span> </>}{bargainText(b)}
          <div className="caption">Từ: {b.deals.join(", ")}</div></li>)}</ul>
        <p className="caption">Cần xem kỹ khi lãi mua rẻ trong năm từ 10% LNTT, hoặc doanh nghiệp lỗ trước thuế. Lãi mua rẻ là thu nhập không có tiền (sinh ra từ đánh giá lại tài sản
          bên bị mua), không lặp lại nếu không có thương vụ mới; bóc ra khi so lợi nhuận và so với dòng tiền kinh doanh.</p>
      </>}
      {data && data.goodwill_moves.length > 0 && <>
        <h3>Biến động lợi thế thương mại</h3>
        <table className="fv-table" aria-label={`Biến động lợi thế thương mại ${symbol}`}>
          <thead><tr><th>Năm</th><th className="num">Đầu năm</th><th className="num">Tăng (thương vụ bạn ghi)</th><th className="num">Phân bổ (thuyết minh)</th>
            <th className="num">Cuối năm</th><th className="num">Giảm khác</th><th className="num">Phân bổ ÷ chi phí quản lý</th><th className="num">Phân bổ ÷ LNTT</th><th></th></tr></thead>
          <tbody>{data.goodwill_moves.map((m) => <tr key={m.year} data-testid="fan-move">
            <td data-label="Năm">{m.year}</td><td className="num" data-label="Đầu năm">{num(m.opening)}</td><td className="num" data-label="Tăng">{num(m.added)}</td>
            <td className="num" data-label="Phân bổ">{m.amortised === null ? "chưa ghi" : num(m.amortised)}</td><td className="num" data-label="Cuối năm">{num(m.closing)}</td>
            <td className="num" data-label="Giảm khác">{m.other === null ? <span className="caption">giảm {signed(m.decline)}</span> : signed(m.other)}</td>
            <td className="num" data-label="Phân bổ ÷ chi phí quản lý">{m.to_admin === null ? "—" : pct(m.to_admin)}</td>
            <td className="num" data-label="Phân bổ ÷ LNTT">{m.to_pbt === null ? "—" : pct(m.to_pbt)}</td>
            <td className="actions"><button type="button" className="btn" aria-label={`Ghi phân bổ ${m.year}`} onClick={() => amortise(m.year, m.amortised)}>
              <Pencil size={14} aria-hidden="true" />Ghi phân bổ</button></td>
          </tr>)}</tbody>
        </table>
        <p className="caption">Đầu năm, cuối năm: báo cáo VNDirect đã lưu (tỷ đồng). Tăng: lợi thế thương mại dương của các thương vụ bạn ghi trong năm. Phân bổ: số bạn ghi từ thuyết
          minh, vì dòng phân bổ của VNDirect thường để trống. Giảm khác = đầu năm + tăng − phân bổ − cuối năm: thoái vốn, xóa sổ hay thương vụ chưa ghi, báo cáo không tách được.
          Chưa ghi phân bổ thì hiện tổng mức giảm. Phân bổ nằm trong chi phí quản lý doanh nghiệp.</p>
      </>}
      <p className="caption">Bạn tự đọc thuyết minh báo cáo tài chính và nhập; VNDirect không có nội dung thuyết minh. XDCB và nguyên giá ở cột &quot;Số của cả công ty&quot; là số dư
        của cả doanh nghiệp từ báo cáo đã lưu, báo cáo không tách theo dự án, nên phần mềm không tự kết luận dự án đã xong. Khi báo cáo của quý hoàn thành dự kiến về, Việc cần
        xem có một dòng nhắc (không gửi Telegram) đến khi bạn bấm Đã hoàn thành hoặc Lùi hạn. Khung khấu hao chỉ để đọc lại. Không phải khuyến nghị.</p>
    </section>
  );
}
