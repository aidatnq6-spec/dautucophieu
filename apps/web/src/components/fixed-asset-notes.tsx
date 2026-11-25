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
type Data = { symbol: string; version: number; projects: Project[]; ranges: Ranges; groups: Record<string, string>; prepaid: Prepaid[]; prepaid_kinds: Record<string, string> };
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
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const rangesRaw = (groups: Record<string, { from: string | number; to: string | number }>, period: string | null) => ({ ...groups, period });
  const keptRanges = () => rangesRaw(data?.ranges.groups ?? {}, data?.ranges.period ?? null);
  const others = (id?: string) => (data?.projects ?? []).filter((p) => p.id !== id).map((p) => toRaw(fromProject(p)));
  const saveProjects = (projects: ReturnType<typeof toRaw>[]) => send(base, "PUT", { projects, ranges: keptRanges() });
  const keptPrepaid = (skip?: string) => Object.fromEntries((data?.prepaid ?? []).filter((r) => r.year !== skip)
    .map((r) => [r.year, { ...r.items, ...(r.summed ? {} : { total: r.total }) }]));
  const savePrepaid = (prepaid: Record<string, Record<string, string>>) => send(base, "PUT", { projects: others(), ranges: keptRanges(), prepaid });
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
      <p className="caption">Bạn tự đọc thuyết minh báo cáo tài chính và nhập; VNDirect không có nội dung thuyết minh. XDCB và nguyên giá ở cột &quot;Số của cả công ty&quot; là số dư
        của cả doanh nghiệp từ báo cáo đã lưu, báo cáo không tách theo dự án, nên phần mềm không tự kết luận dự án đã xong. Khi báo cáo của quý hoàn thành dự kiến về, Việc cần
        xem có một dòng nhắc (không gửi Telegram) đến khi bạn bấm Đã hoàn thành hoặc Lùi hạn. Khung khấu hao chỉ để đọc lại. Không phải khuyến nghị.</p>
    </section>
  );
}
