"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Row = { code: string; name: string; price: string; change_pct: string; unchanged_since: string | null; fred_date: string | null };
type Data = { status: string; read_at?: string; rows?: Row[]; line: string | null };

const dm = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const pct = (r: string) => `${Number(r) > 0 ? "+" : Number(r) < 0 ? "−" : ""}${Math.abs(Number(r) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;

/** Chứng khoán châu Á: the last read from VNDirect, shown with when it was read, never a session day it does not give. */
export function AsiaMarkets() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Data>("macro/asia").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Chứng khoán châu Á">
      <h2>Chứng khoán châu Á</h2>
      <p className="caption">Mức thay đổi gần nhất của Nikkei 225, KOSPI, Thượng Hải và Hang Seng theo VNDirect, đọc cùng bản tin sau phiên. VNDirect không ghi
        ngày phiên, nên ứng dụng ghi giờ đọc; chỉ số có giá không đổi từ hôm trước được ghi là chưa có phiên mới, Nikkei được đối chiếu ngày với FRED.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!d && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {d && (d.status === "ok" && d.rows ? <>
        <ul className="bm-list" aria-label="Các chỉ số châu Á">{d.rows.map((r) => <li key={r.code}><strong>{r.name}</strong>{" "}
          {Number(r.price).toLocaleString("vi-VN", { maximumFractionDigits: 2 })}{" "}
          <span className={Number(r.change_pct) > 0 ? "fd-up" : Number(r.change_pct) < 0 ? "fd-down" : undefined}>{pct(r.change_pct)}</span>
          {r.unchanged_since && <span className="caption"> (chưa có phiên mới từ {dm(r.unchanged_since)})</span>}
          {r.fred_date && <span className="caption"> (phiên {dm(r.fred_date)} theo FRED)</span>}</li>)}</ul>
        <p className="caption">Đọc lúc {new Date(d.read_at!).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })}.</p>
      </> : <p className="muted">Chưa đọc: bản tin sau phiên sẽ đọc từ 15:30.</p>)}
    </section>
  );
}
