"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Cell = { macd: string | null; rsi: number | null; zone: string | null; reason: string | null;
  macd_changed?: boolean; previous_macd?: string | null; rsi_changed?: boolean; previous_zone?: string | null };
type Row = { id: string; label: string; note: string | null; cells: Record<string, Cell> };
type Snapshot = { session_date: string; generated_at: string; previous_date: string | null; errors: Record<string, string>;
  groups: { id: string; label: string; rows: Row[] }[] };

const FRAMES = ["M", "W", "D1", "H4", "H1"];
const ZONE: Record<string, string> = { overbought: "quá mua", oversold: "quá bán", neutral: "trung tính" };

/** "down,<0" may wrap after the comma so a narrow card never needs a scrollbar. */
function MacdText({ value }: { value: string }) {
  const [dir, sign] = value.split(",");
  return <>{dir},<wbr />{sign}</>;
}

/** One line per distinct reason, naming its frames: "H4, H1: Nguồn chỉ có giá ngày". */
function notes(row: Row): string[] {
  const reasons = new Map<string, string[]>();
  for (const f of FRAMES) {
    const r = row.cells[f]?.reason;
    if (r) reasons.set(r, [...(reasons.get(r) ?? []), f]);
  }
  const changed = FRAMES.flatMap((f) => {
    const c = row.cells[f];
    return [
      ...(c?.macd_changed && c.previous_macd ? [`${f} MACD trước: ${c.previous_macd}`] : []),
      ...(c?.rsi_changed && c.previous_zone ? [`${f} RSI trước: ${ZONE[c.previous_zone] ?? c.previous_zone}`] : []),
    ];
  });
  return [...[...reasons].map(([r, fs]) => `${fs.join(", ")}: ${r}`), ...(changed.length ? [`Đổi so với phiên trước — ${changed.join("; ")}`] : [])];
}

function Card({ row }: { row: Row }) {
  return (
    <section className="trend-card" aria-label={row.label}>
      <h3>{row.label}</h3>
      <table className="trend-table" aria-label={row.label}>
        <colgroup><col className="trend-head-col" />{FRAMES.map((f) => <col key={f} />)}</colgroup>
        <thead><tr><th scope="col"><span className="visually-hidden">Chỉ báo</span></th>{FRAMES.map((f) => <th key={f} scope="col">{f}</th>)}</tr></thead>
        <tbody>
          <tr>
            <th scope="row">MACD</th>
            {FRAMES.map((f) => {
              const c = row.cells[f];
              if (!c?.macd) return <td key={f} className="trend-gap" title={c?.reason ?? undefined}>—</td>;
              return <td key={f} className={`trend-macd ${c.macd.startsWith("up") ? "up" : "down"}${c.macd_changed ? " changed" : ""}`}
                title={c.macd_changed && c.previous_macd ? `trước: ${c.previous_macd}` : undefined}><MacdText value={c.macd} /></td>;
            })}
          </tr>
          <tr>
            <th scope="row">RSI</th>
            {FRAMES.map((f) => {
              const c = row.cells[f];
              if (c?.rsi === null || c?.rsi === undefined) return <td key={f} className="trend-gap" title={c?.reason ?? undefined}>—</td>;
              return <td key={f} className={`trend-rsi ${c.zone ?? ""}${c.rsi_changed ? " changed" : ""}`}
                title={c.zone ? ZONE[c.zone] : undefined}>{c.rsi}</td>;
            })}
          </tr>
        </tbody>
      </table>
      {[...notes(row), ...(row.note ? [row.note] : [])].map((n) => <p key={n} className="trend-note">{n}</p>)}
    </section>
  );
}

export function TrendView() {
  const [data, setData] = useState<Snapshot | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<{ snapshot: Snapshot | null }>("trend").then((d) => setData(d.snapshot), (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (data === undefined) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  if (data === null) return <p className="muted">Chưa có bảng: bảng được lập tự động từ 15:30 mỗi phiên giao dịch.</p>;
  return (
    <>
      <p className="notice">Phiên {data.session_date} · lập lúc {new Date(data.generated_at).toLocaleString("vi-VN")} ·{" "}
        {data.previous_date ? `ô viền đậm là ô đổi trạng thái so với phiên ${data.previous_date}` : "chưa có phiên trước để so sánh"}.
        Chỉ để theo dõi, không phải khuyến nghị.</p>
      <div className="trend-legend" aria-label="Chú thích">
        <span className="trend-macd up">up</span> MACD trên đường tín hiệu
        <span className="trend-macd down">down</span> MACD dưới đường tín hiệu
        <span>&gt;0 / &lt;0: MACD so với mức 0</span>
        <span className="trend-rsi overbought">RSI ≥ 70</span> quá mua
        <span className="trend-rsi oversold">RSI ≤ 30</span> quá bán
        <span className="trend-macd changed">viền</span> vừa đổi
      </div>
      {data.groups.map((g) => (
        <section key={g.id} className="surface" aria-label={g.label}>
          <h2>{g.label}</h2>
          <div className="trend-grid">{g.rows.map((r) => <Card key={r.id} row={r} />)}</div>
        </section>
      ))}
    </>
  );
}
