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

function MacdCell({ c }: { c: Cell }) {
  if (!c.macd) return <td className="trend-gap">—{c.reason && <div className="caption">{c.reason}</div>}</td>;
  return (
    <td className={`trend-macd ${c.macd.startsWith("up") ? "up" : "down"}${c.macd_changed ? " changed" : ""}`}>
      {c.macd}{c.macd_changed && c.previous_macd && <div className="caption">trước: {c.previous_macd}</div>}
    </td>
  );
}

function RsiCell({ c }: { c: Cell }) {
  if (c.rsi === null) return <td className="trend-gap">—</td>;
  return (
    <td className={`num trend-rsi ${c.zone ?? ""}${c.rsi_changed ? " changed" : ""}`}>
      {c.rsi}{c.rsi_changed && c.previous_zone && <div className="caption">trước: {ZONE[c.previous_zone] ?? c.previous_zone}</div>}
    </td>
  );
}

function Card({ row }: { row: Row }) {
  return (
    <div className="trend-card">
      <h3>{row.label}</h3>
      <div className="tablewrap">
        <table aria-label={row.label}>
          <thead><tr><th>Chỉ báo</th>{FRAMES.map((f) => <th key={f}>{f}</th>)}</tr></thead>
          <tbody>
            <tr><th scope="row">MACD</th>{FRAMES.map((f) => <MacdCell key={f} c={row.cells[f]} />)}</tr>
            <tr><th scope="row">RSI</th>{FRAMES.map((f) => <RsiCell key={f} c={row.cells[f]} />)}</tr>
          </tbody>
        </table>
      </div>
      {row.note && <p className="caption">{row.note}</p>}
    </div>
  );
}

export function TrendView() {
  const [data, setData] = useState<Snapshot | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<{ snapshot: Snapshot | null }>("trend").then((d) => setData(d.snapshot), (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (data === undefined) return <p className="muted">Đang tải…</p>;
  if (data === null) return <p className="muted">Chưa có bảng: bảng được lập tự động từ 15:30 mỗi phiên giao dịch.</p>;
  return (
    <>
      <p className="notice">Phiên {data.session_date} · lập lúc {new Date(data.generated_at).toLocaleString("vi-VN")} ·{" "}
        {data.previous_date ? `ô viền đậm là ô đổi trạng thái so với phiên ${data.previous_date}` : "chưa có phiên trước để so sánh"}.
        MACD 12-26-9 (up/down: so với đường tín hiệu; &gt;0/&lt;0: so với mức 0), RSI 14. Chỉ để theo dõi, không phải khuyến nghị.</p>
      {data.groups.map((g) => (
        <section key={g.id} className="surface" aria-label={g.label}>
          <h2>{g.label}</h2>
          <div className="trend-grid">{g.rows.map((r) => <Card key={r.id} row={r} />)}</div>
        </section>
      ))}
    </>
  );
}
