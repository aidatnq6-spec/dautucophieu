"use client";
import { Fragment, useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, hanoiDate } from "../lib/format";

type Row = { id: string; label: string; unit: string; auto: boolean; value: string | null; date: string | null; previous: string | null;
  trend: string | null; assessment: string | null; stale: boolean; source_url: string; note: string | null;
  source_error: string | null; manual_allowed: boolean };

/** Keeps the value's own precision (at most two places) with Vietnamese grouping. */
const show = (v: string) => formatDecimal(v, Math.min((v.split(".")[1] ?? "").length, 2));
const TONE: Record<string, string> = { "Tốt": "good", "Xấu": "bad", "Trung tính": "" };

/** The figure's day as dd/mm/yyyy and how long ago that is (days counted on calendar dates, both in Vietnam time). */
export function updatedLabel(day: string | null, today: string): { day: string; ago: string } | null {
  if (!day) return null;
  const [y, m, d] = day.split("-");
  const days = Math.round((Date.UTC(+today.slice(0, 4), +today.slice(5, 7) - 1, +today.slice(8, 10)) - Date.UTC(+y, +m - 1, +d)) / 86_400_000);
  return { day: `${d}/${m}/${y}`, ago: days <= 0 ? "hôm nay" : days === 1 ? "hôm qua" : `${days} ngày trước` };
}

function EntryForm({ row, onDone }: { row: Row; onDone: (saved: boolean) => void }) {
  const [day, setDay] = useState(hanoiDate());
  const [value, setValue] = useState("");
  const [link, setLink] = useState("");
  const [error, setError] = useState<string | null>(null);
  const save = async () => {
    setError(null);
    try {
      await api(`macro/${row.id}/observations`, { method: "POST", body: { date: day, value, source_url: link.trim() || null } });
      onDone(true);
    } catch (e) {
      setError(e instanceof ApiError ? (e.failure.fields.includes("source_url") ? "Link nguồn phải bắt đầu bằng http:// hoặc https://." : e.failure.message) : "Lỗi lưu.");
    }
  };
  return (
    <form aria-label={`Nhập ${row.label}`} className="formgrid" onSubmit={(e) => { e.preventDefault(); void save(); }}>
      <label className="field">Ngày số liệu<input type="date" value={day} onChange={(e) => setDay(e.target.value)} required /></label>
      <label className="field">Giá trị ({row.unit})<input inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} required /></label>
      <label className="field">Link nguồn<input type="url" value={link} onChange={(e) => setLink(e.target.value)} placeholder={row.source_url} /></label>
      <div className="actions"><button className="btn primary" type="submit">Lưu</button><button className="btn" type="button" onClick={() => onDone(false)}>Hủy</button></div>
      {error && <p className="errors" role="alert">{error}</p>}
    </form>
  );
}

export function MacroView() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const load = useCallback(() => api<{ rows: Row[] }>("macro").then((d) => setRows(d.rows), (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")), []);
  useEffect(() => { void load(); }, [load]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!rows) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  // Hand-entered indicators last, highlighted, so they are easy to find after a Telegram reminder.
  const ordered = [...rows.filter((r) => r.auto), ...rows.filter((r) => !r.auto)];
  const today = hanoiDate();
  const tally = rows.reduce((t, r) => ({ ...t, [r.assessment ?? "—"]: (t[r.assessment ?? "—"] ?? 0) + 1 }), {} as Record<string, number>);
  return (
    <section className="surface">
      <p className="notice">Tổng hợp: {tally["Tốt"] ?? 0} Tốt · {tally["Xấu"] ?? 0} Xấu · {tally["Trung tính"] ?? 0} Trung tính · {tally["—"] ?? 0} chưa đủ số liệu.
        Đánh giá theo quy tắc trong bảng của bạn (so với kỳ trước), không phải khuyến nghị mua bán.</p>
      <table aria-label="Chỉ số vĩ mô" className="macro-table">
        <colgroup><col className="mt-n" /><col /><col className="mt-value" /><col className="mt-trend" /><col className="mt-verdict" /><col className="mt-date" /><col className="mt-source" /></colgroup>
        <thead><tr><th>STT</th><th>Biến số</th><th className="num">Hiện tại</th><th>Xu hướng</th><th>Đánh giá</th><th>Cập nhật</th><th>Nguồn</th></tr></thead>
        <tbody>{ordered.map((r, i) => {
          const when = updatedLabel(r.date, today);
          return (
            <Fragment key={r.id}>
              <tr className={r.auto ? undefined : "macro-manual"}>
                <td className="mt-n">{i + 1}</td>
                <td className="mt-name"><strong>{r.label}</strong>{r.note && <div className="caption mt-note">{r.note}</div>}</td>
                <td className="num" data-label="Hiện tại">{r.value ? <><strong>{show(r.value)}</strong> <span className="caption">{r.unit}</span></> : <span className="muted">Chưa có số liệu</span>}
                  {r.previous && <div className="caption">kỳ trước {show(r.previous)}</div>}</td>
                <td data-label="Xu hướng">{r.trend ?? "—"}</td>
                <td data-label="Đánh giá">{r.assessment ? <span className={`pill ${TONE[r.assessment] ?? ""}`}>{r.assessment}</span> : "—"}</td>
                <td className="mt-when" data-label="Cập nhật"><span className="mt-day">{when ? when.day : "—"}</span>
                  <div className="caption">{when && <>{when.ago} · </>}{r.auto ? "Tự động" : "Nhập tay"}{r.stale && <> · <span className="negative">số liệu cũ</span></>}</div>
                  {r.source_error && <div className="caption negative">Lỗi nguồn lần gần nhất{r.manual_allowed ? "; có thể nhập tay" : ""}</div>}</td>
                <td className="mt-actions"><a href={r.source_url} target="_blank" rel="noreferrer noopener">Nguồn</a>
                  {r.manual_allowed && editing !== r.id && <button className="btn" onClick={() => setEditing(r.id)}>Nhập</button>}</td>
              </tr>
              {editing === r.id && <tr className="mt-form"><td colSpan={7}><EntryForm row={r} onDone={(saved) => { setEditing(null); if (saved) void load(); }} /></td></tr>}
            </Fragment>);
        })}
        </tbody>
      </table>
      <p className="caption">Mỗi biến số ghi nguồn ở cột Nguồn và ghi chú dưới tên khi cần. Số tự động cập nhật mỗi lần lịch chạy (08:30, 15:30, 20:00); khi nguồn chính
        lỗi thì lấy nguồn dự phòng, nếu vẫn lỗi thì báo lỗi nguồn và cho nhập tay kèm link. Ngày ở cột Cập nhật là ngày của số liệu, không phải ngày tải về.</p>
    </section>
  );
}
