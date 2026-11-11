"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Row = { quarter: string; report_day: string | null; base_day: string | null; reason: string | null; profit_yoy: string | null; profit_turn: string | null;
  after_5: string | null; after_20: string | null; index_20: string | null; excess_20: string | null };
type Summary = { compared: number; good_sold: number; bad_bought: number; same_way: number };
type Data = { rows: Row[]; summary: Summary };

const q = (p: string) => `Q${p.slice(-1)}/${p.slice(0, 4)}`;
const day = (d: string) => d.split("-").reverse().join("/");
const pct = (v: string | null) => {
  if (v === null) return "—";
  const n = Math.round(Number(v) * 1000) / 10;
  return `${n > 0 ? "+" : n < 0 ? "−" : ""}${Math.abs(n).toLocaleString("vi-VN")}%`;
};
const tone = (v: string | null) => (v === null ? "" : Number(v) > 0 ? " positive" : Number(v) < 0 ? " negative" : "");

/** One line over the quarters compared. */
export function summaryText(s: Summary): string {
  if (!s.compared) return "Chưa có quý nào đủ ngày ra báo cáo và giá 20 phiên sau đó.";
  return `${s.compared} quý có đủ số: ${s.good_sold} lần lợi nhuận tăng mà giá giảm sau 20 phiên, ${s.bad_bought} lần lợi nhuận giảm mà giá tăng, `
    + `${s.same_way} lần giá đi cùng chiều lợi nhuận.`;
}

export function ReportReaction({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Data | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<Data>(`stock/${encodeURIComponent(symbol)}/reaction`).then(setData, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (!data && !message) return null;
  return (
    <section className="surface" aria-label="Phản ứng giá sau báo cáo">
      <h2>Phản ứng giá sau báo cáo</h2>
      {message ? <p className="muted">{message}</p> : data && <>
        <p data-testid="reaction-summary">{summaryText(data.summary)}</p>
        <table className="fv-table" aria-label={`Phản ứng giá sau báo cáo ${symbol}`}>
          <thead><tr><th>Quý</th><th>Ngày có báo cáo</th><th className="num">LNST so cùng kỳ</th><th className="num">Giá 5 phiên sau</th>
            <th className="num">Giá 20 phiên sau</th><th className="num">Hơn/kém VN-Index (20 phiên)</th></tr></thead>
          <tbody>{[...data.rows].reverse().map((r) => <tr key={r.quarter}>
            <td data-label="Quý">{q(r.quarter)}</td>
            <td data-label="Ngày có báo cáo">{r.report_day ? day(r.report_day) : <span className="muted">chưa có ngày</span>}</td>
            <td className={`num${tone(r.profit_yoy)}`} data-label="LNST so cùng kỳ">{r.profit_turn === "to_profit" ? "lãi lại" : r.profit_turn === "to_loss" ? "lỗ" : pct(r.profit_yoy)}</td>
            <td className={`num${tone(r.after_5)}`} data-label="Giá 5 phiên sau">{pct(r.after_5)}</td>
            <td className={`num${tone(r.after_20)}`} data-label="Giá 20 phiên sau">{pct(r.after_20)}</td>
            <td className={`num${tone(r.excess_20)}`} data-label="Hơn/kém VN-Index">{pct(r.excess_20)}</td>
          </tr>)}</tbody>
        </table>
        <p className="caption">Ngày có báo cáo là ngày VNDirect có số liệu của quý (thường trùng hoặc sát ngày công bố); quý cũ được nạp bù sau nên không có ngày. Giá
          so với phiên đóng cửa ngay trước ngày đó, giá đã điều chỉnh. Cho thấy thị trường đã phản ứng thế nào, không phải dự báo lần tới. Không phải khuyến nghị.</p>
      </>}
    </section>
  );
}
