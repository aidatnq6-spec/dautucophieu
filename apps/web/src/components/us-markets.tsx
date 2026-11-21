"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

export type UsRow = { id: string; series: string; name: string; close: string; date: string; day_pct: string | null; m1_pct: string | null; stale: boolean };
type Data = { rows: UsRow[]; source: string };

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** A change on a share as a signed percentage, "—" when there is nothing to compare. */
export function usPct(r: string | null): string {
  if (r === null) return "—";
  const v = Number(r) * 100;
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

const tone = (r: string | null) => (r === null ? undefined : Number(r) > 0 ? "fd-up" : Number(r) < 0 ? "fd-down" : undefined);

/** Chứng khoán Mỹ: S&P 500, Nasdaq and Dow Jones from FRED, each with its own session date. */
export function UsMarkets() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Data>("macro/us").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Chứng khoán Mỹ">
      <h2>Chứng khoán Mỹ</h2>
      <p className="caption">Điểm đóng cửa của S&amp;P 500, Nasdaq Composite và Dow Jones theo FRED, kèm ngày phiên; thay đổi so với phiên trước và so với
        30 ngày trước. Cập nhật cùng lượt vĩ mô; phiên Mỹ kết thúc lúc rạng sáng giờ Việt Nam.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!d && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {d && (d.rows.length === 0 ? <p className="muted">Chưa có số: lượt vĩ mô kế tiếp sẽ đọc từ FRED.</p> :
        <ul className="bm-list" aria-label="Các chỉ số Mỹ">{d.rows.map((r) => <li key={r.id}><strong>{r.name}</strong>{" "}
          {Number(r.close).toLocaleString("vi-VN", { maximumFractionDigits: 2 })}{" "}
          <span className={tone(r.day_pct)}>{usPct(r.day_pct)}</span>
          <span className="caption"> · 30 ngày <span className={tone(r.m1_pct)}>{usPct(r.m1_pct)}</span> · phiên {dmy(r.date)}</span>
          {r.stale && <span className="caption negative"> (số cũ, quá 7 ngày)</span>}</li>)}</ul>)}
    </section>
  );
}
