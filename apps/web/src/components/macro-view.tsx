"use client";
import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, hanoiDate } from "../lib/format";

type Row = { id: string; label: string; unit: string; auto: boolean; value: string | null; date: string | null; previous: string | null;
  trend: string | null; assessment: string | null; stale: boolean; source_url: string; note: string | null;
  source_error: string | null; manual_allowed: boolean };

/** Keeps the value's own precision (at most two places) with Vietnamese grouping. */
const show = (v: string) => formatDecimal(v, Math.min((v.split(".")[1] ?? "").length, 2));
const TONE: Record<string, string> = { "Tốt": "good", "Xấu": "bad", "Trung tính": "" };

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
  if (!rows) return <p className="muted">Đang tải…</p>;
  const tally = rows.reduce((t, r) => ({ ...t, [r.assessment ?? "—"]: (t[r.assessment ?? "—"] ?? 0) + 1 }), {} as Record<string, number>);
  return (
    <section className="surface">
      <p className="notice">Tổng hợp: {tally["Tốt"] ?? 0} Tốt · {tally["Xấu"] ?? 0} Xấu · {tally["Trung tính"] ?? 0} Trung tính · {tally["—"] ?? 0} chưa đủ số liệu.
        Đánh giá theo quy tắc trong bảng của bạn (so với kỳ trước), không phải khuyến nghị mua bán.</p>
      <div className="tablewrap">
        <table aria-label="Chỉ số vĩ mô">
          <thead><tr><th>STT</th><th>Biến số</th><th className="num">Hiện tại</th><th>Xu hướng</th><th>Đánh giá</th><th>Cập nhật</th><th>Nguồn</th></tr></thead>
          <tbody>{rows.map((r, i) => (
            <tr key={r.id}>
              <td>{i + 1}</td>
              <td>{r.label}{r.note && <div className="caption">{r.note}</div>}</td>
              <td className="num">{r.value ? <>{show(r.value)} <span className="caption">{r.unit}</span></> : <span className="muted">Chưa có số liệu</span>}
                {r.previous && <div className="caption">kỳ trước {show(r.previous)}</div>}</td>
              <td>{r.trend ?? "—"}</td>
              <td>{r.assessment ? <span className={`pill ${TONE[r.assessment] ?? ""}`}>{r.assessment}</span> : "—"}</td>
              <td>{r.date ?? "—"}{r.stale && <div className="caption">số liệu cũ</div>}
                <div className="caption">{r.auto ? "Tự động" : "Nhập tay"}</div>
                {r.source_error && <div className="caption negative">Lỗi nguồn lần cập nhật gần nhất{r.manual_allowed ? "; có thể nhập tay" : ""}</div>}
                {r.manual_allowed && editing !== r.id && <button className="btn" onClick={() => setEditing(r.id)}>Nhập</button>}
                {editing === r.id && <EntryForm row={r} onDone={(saved) => { setEditing(null); if (saved) void load(); }} />}</td>
              <td><a href={r.source_url} target="_blank" rel="noreferrer noopener">Nguồn</a></td>
            </tr>))}
          </tbody>
        </table>
      </div>
      <p className="caption">Tự động: FRED (Fed St. Louis), tỷ giá Vietcombank và trang Topi (tỷ giá tự do, NHNN, lãi suất tiền gửi; đọc từ nội dung trang nên
        nếu Topi đổi giao diện sẽ báo lỗi nguồn và cho nhập tay), cập nhật mỗi lần lịch chạy. Khối ngoại, PMI, M2, lãi suất liên ngân hàng, lợi suất trái phiếu
        Việt Nam và giá trị giao dịch không có nguồn miễn phí hợp lệ nên nhập tay kèm link nguồn.</p>
    </section>
  );
}
