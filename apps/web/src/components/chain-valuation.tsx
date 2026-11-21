"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Side = { now: string | null; median_5y: string | null; position: string | null; n: number; weeks: number };
export type ChainValue = { id: string; name: string; members: number; priced: number; no_data: string[]; stale: string[]; pe: Side; pb: Side;
  since: string | null };

const num = (v: string | null, d = 1) => (v === null ? "—" : Number(v).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d }));

/** Where today sits in the five years: "rẻ" in the lowest fifth, "đắt" in the top fifth. */
export function positionWord(position: string | null): { text: string; tone: string } {
  if (position === null) return { text: "—", tone: "" };
  const p = Number(position), pct = `${Math.round(p * 100)}%`;
  return p <= 0.2 ? { text: `${pct} · rẻ`, tone: "good" } : p >= 0.8 ? { text: `${pct} · đắt`, tone: "bad" } : { text: pct, tone: "" };
}

/** Định giá chuỗi so với 5 năm: each chain's median P/E and P/B now against its own five years. */
export function ChainValuation() {
  const [rows, setRows] = useState<ChainValue[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<{ chains: ChainValue[] }>("market/value-chains/valuation").then((d) => setRows(d.chains),
    (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const sorted = rows ? [...rows].sort((a, b) => Number(a.pe.position ?? 2) - Number(b.pe.position ?? 2)) : null;
  return (
    <section className="surface" aria-label="Định giá chuỗi so với 5 năm">
      <h2>Định giá chuỗi so với 5 năm</h2>
      <p className="caption">P/E (lợi nhuận 4 quý) và P/B trung vị của các mã trong chuỗi, theo tuần; mỗi tuần chỉ dùng báo cáo đã công bố đến tuần đó
        (quý tính từ 45 ngày sau khi kết thúc). Vị trí 0% là rẻ nhất, 100% là đắt nhất trong 5 năm; so với trung vị 5 năm. Lỗ thì không có P/E.
        Chuỗi ít mã thì trung vị chính là mã đó. Chỉ mô tả dữ liệu, không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!rows && !error && <p className="muted fx-loading" role="status">Đang tính…</p>}
      {sorted && <table className="fv-table" aria-label="Định giá chuỗi">
        <thead><tr><th>Chuỗi</th><th className="num">P/E</th><th className="num">Trung vị 5 năm</th><th>Vị trí P/E</th>
          <th className="num">P/B</th><th className="num">Trung vị 5 năm</th><th>Vị trí P/B</th></tr></thead>
        <tbody>{sorted.map((c) => {
          const pe = positionWord(c.pe.position), pb = positionWord(c.pb.position);
          const left = [c.no_data.length ? `chưa có số: ${c.no_data.join(", ")}` : "", c.stale.length ? `số cũ: ${c.stale.join(", ")}` : "",
            c.since ? `có từ ${c.since.slice(8, 10)}/${c.since.slice(5, 7)}/${c.since.slice(0, 4)}` : ""].filter(Boolean).join(" · ");
          return (
            <tr key={c.id} data-testid={`chain-value-${c.id}`}>
              <td data-label="Chuỗi"><strong>{c.name}</strong> <span className="caption">{c.priced}/{c.members} mã</span>{left && <div className="caption">{left}</div>}</td>
              <td className="num" data-label="P/E">{num(c.pe.now)}</td><td className="num" data-label="Trung vị 5 năm">{num(c.pe.median_5y)}</td>
              <td data-label="Vị trí P/E">{pe.tone ? <span className={`pill ${pe.tone}`}>{pe.text}</span> : pe.text}</td>
              <td className="num" data-label="P/B">{num(c.pb.now, 2)}</td><td className="num" data-label="Trung vị 5 năm">{num(c.pb.median_5y, 2)}</td>
              <td data-label="Vị trí P/B">{pb.tone ? <span className={`pill ${pb.tone}`}>{pb.text}</span> : pb.text}</td>
            </tr>
          );
        })}</tbody>
      </table>}
    </section>
  );
}
