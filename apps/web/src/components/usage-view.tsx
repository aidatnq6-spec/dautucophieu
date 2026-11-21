"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { ApiError, api } from "../lib/api";
import { pageLabel } from "./app-nav";

type PageRow = { page: string; last_30: number; last_7: number; today: number; last_day: string | null };
type SlowRow = { path: string; count: number; worst: string; last: string };
export type Usage = { pages: PageRow[]; slow: SlowRow[]; slow_threshold: string | null; since: string | null };

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const seconds = (v: string) => v.replace(".", ",");

/** Counts each page opened (by its first segment) once per visit; nothing is shown and a failure is ignored. */
export function UsageBeacon() {
  const path = usePathname();
  useEffect(() => {
    if (path) api("usage/visit", { method: "POST", body: { page: path } }).catch(() => undefined);
  }, [path]);
  return null;
}

/** "Đã ghi từ dd/mm/yyyy", or that nothing is recorded yet. */
export function usageSince(u: Usage): string {
  return u.since ? `Đã ghi từ ${dmy(u.since)}.` : "Chưa ghi lượt mở trang nào.";
}

/** Sử dụng phần mềm: which pages are opened most over 30 days and which requests were slow; kept on this computer only. */
export function UsageView() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<Usage>("usage").then(setUsage, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  return (
    <section className="surface" aria-label="Sử dụng phần mềm">
      <h2>Sử dụng phần mềm</h2>
      <p className="caption">Số lần mở từng trang và các yêu cầu chậm hơn {usage?.slow_threshold ? seconds(usage.slow_threshold) : "1"} giây, để chọn
        việc cải tiến tiếp theo. Chỉ lưu trên máy này; đường dẫn chậm đã che mã cổ phiếu và số tiền.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!usage && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {usage && <>
        <p className="caption">{usageSince(usage)}</p>
        {usage.pages.length > 0 && <table className="fv-table" aria-label="Lượt mở trang">
          <thead><tr><th>Trang</th><th className="num">30 ngày</th><th className="num">7 ngày</th><th className="num">Hôm nay</th></tr></thead>
          <tbody>{usage.pages.map((p) => <tr key={p.page}>
            <td data-label="Trang">{pageLabel(p.page)}</td><td className="num" data-label="30 ngày">{p.last_30}</td>
            <td className="num" data-label="7 ngày">{p.last_7}</td><td className="num" data-label="Hôm nay">{p.today}</td></tr>)}</tbody>
        </table>}
        <h3>Yêu cầu chậm</h3>
        {usage.slow.length === 0 ? <p className="muted">Chưa có yêu cầu nào chậm hơn ngưỡng.</p>
          : <table className="fv-table" aria-label="Yêu cầu chậm">
            <thead><tr><th>Đường dẫn</th><th className="num">Số lần</th><th className="num">Lâu nhất</th></tr></thead>
            <tbody>{usage.slow.map((s) => <tr key={s.path}>
              <td data-label="Đường dẫn"><code>{s.path}</code></td><td className="num" data-label="Số lần">{s.count}</td>
              <td className="num" data-label="Lâu nhất">{seconds(s.worst)} giây</td></tr>)}</tbody>
          </table>}
      </>}
    </section>
  );
}
