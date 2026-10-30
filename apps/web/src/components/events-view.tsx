"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

export type Ev = { id: string; symbol: string; kind: string; title: string; key_date: string | null; exright: string | null; record: string | null;
  payout: string | null; ratio: number | null; value_per_share: number | null; held: boolean };
type Data = { upcoming: Ev[]; recent: Ev[]; undated: Ev[]; insider: Ev[]; updated_at: string | null; remind_days: number };

const KIND: Record<string, string> = { dividend_cash: "Cổ tức tiền", issue: "Phát hành", meeting: "Đại hội cổ đông", listing: "Niêm yết thêm",
  other: "Khác", insider: "Giao dịch nội bộ" };
const day = (iso: string | null) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "chưa có ngày");
const vnd = (n: number) => `${n.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} đ/cp`;

function details(e: Ev) {
  const parts: string[] = [];
  if (e.kind === "meeting") parts.push(`họp ${day(e.key_date)}`);
  else if (e.exright) parts.push(`GDKHQ ${day(e.exright)}`);
  if (e.kind === "dividend_cash" && e.value_per_share) parts.push(vnd(e.value_per_share));
  if (e.kind === "issue" && e.ratio) parts.push(`tỷ lệ ${(e.ratio * 100).toLocaleString("vi-VN", { maximumFractionDigits: 2 })}%`);
  if (e.record && e.kind !== "meeting") parts.push(`chốt ${day(e.record)}`);
  if (e.payout) parts.push(`trả ${day(e.payout)}`);
  return parts.join(" · ");
}

export function EventTable({ label, rows, symbol = true }: { label: string; rows: Ev[]; symbol?: boolean }) {
  if (!rows.length) return <p className="muted">Không có.</p>;
  return (
    <table className="fv-table cc-table" aria-label={label}>
      <thead><tr><th>Ngày</th>{symbol && <th>Mã</th>}<th>Loại</th><th>Nội dung</th></tr></thead>
      <tbody>{rows.map((e) => <tr key={e.id}>
        <td data-label="Ngày">{day(e.key_date)}</td>
        {symbol && <td data-label="Mã"><Link href={`/research/${e.symbol}`}>{e.held ? <strong>{e.symbol}</strong> : e.symbol}</Link>
          {e.held && <> <span className="pill good">Đang nắm</span></>}</td>}
        <td data-label="Loại">{KIND[e.kind] ?? e.kind}</td>
        <td data-label="Nội dung">{e.title}{details(e) && <div className="caption">{details(e)}</div>}</td>
      </tr>)}</tbody>
    </table>
  );
}

/** Corporate events of the watched tickers; Telegram reminders go out separately, 5 days ahead. */
export function EventsView() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [insider, setInsider] = useState(false);
  useEffect(() => { api<Data>("events").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!d) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  return (
    <>
      <p className="notice">Cổ tức, phát hành và đại hội cổ đông của 50 mã đang theo dõi (Vnstock){d.updated_at ? `, cập nhật ${new Date(d.updated_at).toLocaleString("vi-VN")}` : ""}.
        Ứng dụng nhắc qua Telegram trước {d.remind_days} ngày (theo ngày GDKHQ hoặc ngày họp), mỗi sự kiện một lần. Chỉ để theo dõi, không phải khuyến nghị.</p>
      <section className="surface"><h2>Sắp tới (60 ngày)</h2><EventTable label="Sự kiện sắp tới" rows={d.upcoming} /></section>
      <section className="surface"><h2>Đã qua (30 ngày)</h2><EventTable label="Sự kiện đã qua" rows={d.recent} /></section>
      {d.undated.length > 0 && <section className="surface"><h2>Chưa có ngày</h2><p className="caption">Không nhắc vì chưa có ngày GDKHQ hoặc ngày họp.</p>
        <EventTable label="Sự kiện chưa có ngày" rows={d.undated} /></section>}
      <section className="surface">
        <button className="btn" aria-expanded={insider} onClick={() => setInsider(!insider)}>
          {insider ? "Ẩn" : "Xem"} giao dịch nội bộ 30 ngày qua ({d.insider.length})</button>
        {insider && <EventTable label="Giao dịch nội bộ" rows={d.insider} />}
      </section>
    </>
  );
}
