"use client";
import { useEffect, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { ApiError, api } from "../lib/api";

type Project = { id: string; name: string; total: string | null; booked: string | null; by_year: Record<string, string>; source_url: string | null; note: string;
  planned: string; remaining: string | null; unplaced: string | null };
type Data = { symbol: string; version: number; years: { year: string; amount: string; projects: number }[]; projects: Project[] };
type Draft = { id?: string; name: string; total: string; booked: string; years: { year: string; amount: string }[]; source_url: string; note: string };

const ty = (v: string | null) => (v === null ? "—" : Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 1 }));
const requestId = () => `prj-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const blank = (): Draft => ({ name: "", total: "", booked: "", years: [{ year: String(new Date().getFullYear()), amount: "" }], source_url: "", note: "" });

/** The owner's yearly figures on one line. */
export function yearsLine(byYear: Record<string, string>): string {
  const entries = Object.entries(byYear);
  return entries.length ? entries.map(([y, v]) => `${y}: ${ty(v)}`).join(" · ") : "—";
}

function toRaw(d: Draft) {
  return { ...(d.id ? { id: d.id } : {}), name: d.name, total: d.total || null, booked: d.booked || null, source_url: d.source_url || null, note: d.note,
    by_year: Object.fromEntries(d.years.filter((y) => y.year.trim() && y.amount.trim()).map((y) => [y.year.trim(), y.amount.trim()])) };
}

function fromProject(p: Project): Draft {
  return { id: p.id, name: p.name, total: p.total ?? "", booked: p.booked ?? "", source_url: p.source_url ?? "", note: p.note,
    years: Object.entries(p.by_year).map(([year, amount]) => ({ year, amount })) };
}

export function PropertyProjects({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Data | null>(null);
  const [hidden, setHidden] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<Data>(`stock/${encodeURIComponent(symbol)}/projects`).then(setData, (e) => {
      if (e instanceof ApiError && e.failure.code === "not_a_developer") setHidden(true); else setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
    });
  }, [symbol]);
  if (hidden || (!data && !message)) return null;
  async function save(projects: ReturnType<typeof toRaw>[]) {
    if (!data) return;
    try {
      setData(await api<Data>(`stock/${encodeURIComponent(symbol)}/projects`, { method: "PUT", body: { projects, expected_version: data.version, request_id: requestId() } }));
      setDraft(null);
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const others = (id?: string) => (data?.projects ?? []).filter((p) => p.id !== id).map((p) => toRaw(fromProject(p)));
  const max = Math.max(1, ...(data?.years ?? []).map((y) => Number(y.amount)));
  const setYear = (i: number, patch: Partial<{ year: string; amount: string }>) =>
    draft && setDraft({ ...draft, years: draft.years.map((x, j) => (j === i ? { ...x, ...patch } : x)) });
  return (
    <section className="surface" aria-label="Dự án và điểm rơi lợi nhuận">
      <h2>Dự án và điểm rơi lợi nhuận</h2>
      {message && <p className="errors" role="alert">{message}</p>}
      {data && data.years.length > 0 && <div className="pp-years" aria-label="Doanh thu dự kiến ghi nhận theo năm">
        {data.years.map((y) => <div key={y.year} className="pp-year"><span>{y.year}</span>
          <span className="pp-bar" style={{ width: `${Math.max(4, (Number(y.amount) / max) * 100)}%` }} />
          <strong>{ty(y.amount)} tỷ</strong><span className="caption">{y.projects} dự án</span></div>)}
      </div>}
      {data && data.projects.length > 0 ? <table className="fv-table" aria-label={`Dự án ${symbol}`}>
        <thead><tr><th>Dự án</th><th className="num">Tổng dự kiến (tỷ)</th><th className="num">Đã ghi nhận</th><th>Dự kiến theo năm</th><th className="num">Chưa xếp năm</th><th></th></tr></thead>
        <tbody>{data.projects.map((p) => <tr key={p.id}>
          <td data-label="Dự án">{p.source_url ? <a href={p.source_url} target="_blank" rel="noreferrer noopener">{p.name}</a> : p.name}
            {p.note && <div className="caption">{p.note}</div>}</td>
          <td className="num" data-label="Tổng dự kiến">{ty(p.total)}</td>
          <td className="num" data-label="Đã ghi nhận">{ty(p.booked)}</td>
          <td data-label="Dự kiến theo năm">{yearsLine(p.by_year)}</td>
          <td className={`num${p.unplaced !== null && Number(p.unplaced) !== 0 ? " negative" : ""}`} data-label="Chưa xếp năm">{ty(p.unplaced)}</td>
          <td className="actions">
            <button type="button" className="btn" aria-label={`Sửa ${p.name}`} onClick={() => setDraft(fromProject(p))}><Pencil size={14} aria-hidden="true" />Sửa</button>
            <button type="button" className="btn" aria-label={`Xóa ${p.name}`} onClick={() => { if (window.confirm(`Xóa dự án ${p.name}?`)) void save(others(p.id)); }}>
              <Trash2 size={14} aria-hidden="true" />Xóa</button></td>
        </tr>)}</tbody>
      </table> : data && <p className="muted">Chưa có dự án nào. Ghi các dự án chính từ báo cáo thường niên, nghị quyết hay tài liệu gặp nhà đầu tư của doanh nghiệp.</p>}
      {!draft && data && <button type="button" className="btn" onClick={() => setDraft(blank())}><Plus size={15} aria-hidden="true" />Thêm dự án</button>}
      {draft && <form className="pp-form" aria-label="Dự án" onSubmit={(e) => { e.preventDefault(); void save([...others(draft.id), toRaw(draft)]); }}>
        <label className="field">Tên dự án<input value={draft.name} maxLength={120} required onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></label>
        <label className="field">Tổng doanh thu dự kiến (tỷ đồng)<input inputMode="decimal" value={draft.total} onChange={(e) => setDraft({ ...draft, total: e.target.value })} /></label>
        <label className="field">Đã ghi nhận đến nay (tỷ đồng)<input inputMode="decimal" value={draft.booked} onChange={(e) => setDraft({ ...draft, booked: e.target.value })} /></label>
        <fieldset><legend>Dự kiến ghi nhận theo năm (tỷ đồng)</legend>
          {draft.years.map((y, i) => <div key={i} className="row">
            <label className="field">Năm<input inputMode="numeric" value={y.year} maxLength={4} onChange={(e) => setYear(i, { year: e.target.value })} /></label>
            <label className="field">Số tỷ<input inputMode="decimal" value={y.amount} onChange={(e) => setYear(i, { amount: e.target.value })} /></label>
          </div>)}
          <button type="button" className="btn" onClick={() => setDraft({ ...draft, years: [...draft.years,
            { year: String(Number(draft.years.at(-1)?.year || new Date().getFullYear()) + 1), amount: "" }] })}>
            <Plus size={15} aria-hidden="true" />Thêm năm</button>
        </fieldset>
        <label className="field">Link tài liệu nguồn<input type="url" value={draft.source_url} onChange={(e) => setDraft({ ...draft, source_url: e.target.value })} placeholder="https://…" /></label>
        <label className="field">Ghi chú<input value={draft.note} maxLength={500} onChange={(e) => setDraft({ ...draft, note: e.target.value })} /></label>
        <div className="row"><button className="btn primary" type="submit">Lưu dự án</button><button className="btn" type="button" onClick={() => setDraft(null)}>Hủy</button></div>
      </form>}
      <p className="caption">Số do bạn đọc từ tài liệu công khai của doanh nghiệp và tự nhập; phần mềm chỉ cộng theo năm, không tự chia hay dự báo. Chưa xếp năm = tổng − đã ghi
        nhận − các năm đã nhập. Lợi nhuận thực tế phụ thuộc tiến độ bàn giao. Không phải khuyến nghị.</p>
    </section>
  );
}
