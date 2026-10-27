"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Fall = { depth: string; peak: string; trough: string; recovered: string | null };
type Row = { symbol: string; since: string | null; max: Fall | null; current: { depth: string; peak: string } | null; price: string | null;
  cost: string | null; vs_cost: string | null; hit: boolean };
type Watch = { symbol: string; since: string | null; max: Fall | null; current: { depth: string; peak: string } | null };
type Data = { threshold: string; rows: Row[]; watch?: Watch[] };

const INDEX_NAME: Record<string, string> = { VNINDEX: "VN-Index", VN30: "VN30" };

function Falls({ r }: { r: Watch }) {
  return <>
    <td data-label="Giảm sâu nhất">{r.max ? <><Signed value={r.max.depth} />
      <div className="caption">{/[1-9]/.test(r.max.depth) ? `${day(r.max.peak)} → ${day(r.max.trough)}, ` : ""}{recovery(r.max)}</div></> : "—"}</td>
    <td data-label="Đang giảm từ đỉnh">{r.current ? <><Signed value={r.current.depth} /><div className="caption">đỉnh {day(r.current.peak)}</div></> : "—"}</td>
  </>;
}

const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const pct = (r: string) => formatRatio(r, 1);

function Signed({ value }: { value: string | null }) {
  if (value === null) return <span className="muted">—</span>;
  const negative = value.startsWith("-"), zero = !/[1-9]/.test(value);
  return <span className={zero ? "" : negative ? "negative" : "positive"}>{zero || negative ? "" : "+"}{pct(value)}</span>;
}

function recovery(f: Fall) {
  if (!/[1-9]/.test(f.depth)) return "chưa từng giảm";
  if (!f.recovered) return "chưa hồi lại đỉnh cũ";
  const months = Math.round((Date.parse(f.recovered) - Date.parse(f.trough)) / (30.44 * 86_400_000));
  return `hồi lại đỉnh ${day(f.recovered)} (sau ${months} tháng)`;
}

/** Deepest falls over the full stored history, the fall now, and price against cost; a reminder only at the owner's own threshold. */
export function DrawdownView() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Data>("drawdown").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const limit = d ? formatRatio(d.threshold, 1).replace(",0%", "%") : "";
  return (
    <section className="surface" aria-label="Kế hoạch sụt giảm">
      <h2>Kế hoạch sụt giảm</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!d && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {d && <>
        <p className="caption">Mức giảm sâu nhất từ một đỉnh trong toàn bộ lịch sử giá đã lưu, mức đang giảm so với đỉnh, và giá so với giá vốn.
          Khi một mã xuống tới ngưỡng {limit} dưới giá vốn (sửa trong Cài đặt), ứng dụng nhắc qua Telegram một lần. Chỉ để tự xem lại kế hoạch,
          không phải khuyến nghị.</p>
        <table className="fv-table cc-table" aria-label="Sụt giảm theo mã">
          <thead><tr><th>Mã</th><th>Giảm sâu nhất</th><th>Đang giảm từ đỉnh</th><th className="num">So với giá vốn</th></tr></thead>
          <tbody>{d.rows.map((r) => <tr key={r.symbol} className={r.hit ? "cc-over" : ""}>
            <td data-label="Mã"><strong>{INDEX_NAME[r.symbol] ?? r.symbol}</strong>
              {r.since && <div className="caption">dữ liệu từ {day(r.since)}</div>}</td>
            <Falls r={r} />
            <td data-label="So với giá vốn" className="num">{INDEX_NAME[r.symbol] ? <span className="muted">—</span> : <>
              <Signed value={r.vs_cost} />{r.hit && <span className="pill bad"> chạm ngưỡng</span>}
              {r.cost && <div className="caption">giá vốn {formatVnd(r.cost, { unit: false })}</div>}</>}</td>
          </tr>)}</tbody>
        </table>
        {d.watch && d.watch.length > 0 && <details className="dd-watch">
          <summary>Các mã đang theo dõi ({d.watch.length})</summary>
          <p className="caption">Mã trong danh sách theo dõi mà bạn chưa nắm, mã đang giảm sâu nhất từ đỉnh xếp trước. Không có nhắc Telegram cho các mã này.</p>
          <table className="fv-table cc-table" aria-label="Sụt giảm các mã đang theo dõi">
            <thead><tr><th>Mã</th><th>Giảm sâu nhất</th><th>Đang giảm từ đỉnh</th></tr></thead>
            <tbody>{d.watch.map((r) => <tr key={r.symbol}>
              <td data-label="Mã"><strong>{r.symbol}</strong>{r.since ? <div className="caption">dữ liệu từ {day(r.since)}</div>
                : <div className="caption">chưa có dữ liệu giá</div>}</td>
              <Falls r={r} />
            </tr>)}</tbody>
          </table>
        </details>}
      </>}
    </section>
  );
}
