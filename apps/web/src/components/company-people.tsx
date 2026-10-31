"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Holder = { name: string; type: string | null; quantity: number | null; percent: number | null; updated: string | null };
type Officer = { name: string; position: string | null; percent: number | null; quantity: number | null };
type View = { symbol: string; shareholders: Holder[]; officers: Officer[]; fetched_at: string | null; stale: boolean; reason: string | null };

const TYPE: Record<string, string> = { Individual: "Cá nhân", Organization: "Tổ chức" };
const day = (iso: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const share = (p: number | null) => (p === null ? "—" : formatRatio(String(p), 2));
const shares = (q: number | null) => (q === null ? "—" : formatVnd(String(q), { unit: false }));
const TOP = 10;

/** Major shareholders (top ten by stake) and officers, from the company's public disclosures (Vnstock, VCI), cached a month. */
export function CompanyPeople({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>(`fairvalue/people/${encodeURIComponent(symbol)}`).then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  const holders = [...(view?.shareholders ?? [])].sort((a, b) => (b.percent ?? -1) - (a.percent ?? -1)).slice(0, TOP);
  return (
    <section className="surface" aria-label="Cổ đông lớn và ban lãnh đạo">
      <h2>Cổ đông lớn và ban lãnh đạo</h2>
      {!view && !message && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {message && <p className="errors" role="alert">{message}</p>}
      {view?.reason && <p className="muted">{view.reason}.</p>}
      {view && !view.reason && <>
        <h3>{Math.min(TOP, view.shareholders.length)} cổ đông lớn nhất</h3>
        <table className="fv-table" aria-label={`Cổ đông lớn ${symbol}`}>
          <thead><tr><th>Cổ đông</th><th>Loại</th><th className="num">Tỷ lệ</th><th className="num">Số cổ phiếu</th><th>Cập nhật</th></tr></thead>
          <tbody>{holders.map((h) => <tr key={h.name}><td data-label="Cổ đông">{h.name}</td><td data-label="Loại">{TYPE[h.type ?? ""] ?? h.type ?? "—"}</td>
            <td data-label="Tỷ lệ" className="num">{share(h.percent)}</td><td data-label="Số cổ phiếu" className="num">{shares(h.quantity)}</td>
            <td data-label="Cập nhật">{day(h.updated)}</td></tr>)}</tbody>
        </table>
        <h3>Ban lãnh đạo</h3>
        <table className="fv-table" aria-label={`Ban lãnh đạo ${symbol}`}>
          <thead><tr><th>Họ tên</th><th>Chức vụ</th><th className="num">Tỷ lệ sở hữu</th><th className="num">Số cổ phiếu</th></tr></thead>
          <tbody>{view.officers.map((o) => <tr key={`${o.name}-${o.position}`}><td data-label="Họ tên">{o.name}</td><td data-label="Chức vụ">{o.position ?? "—"}</td>
            <td data-label="Tỷ lệ sở hữu" className="num">{share(o.percent)}</td><td data-label="Số cổ phiếu" className="num">{shares(o.quantity)}</td></tr>)}</tbody>
        </table>
        <p className="caption">Nguồn: công bố của doanh nghiệp qua Vnstock (VCI), đọc ngày {day(view.fetched_at)}{view.stale ? " — nguồn đang lỗi, đây là bản đã lưu" : ""};
          tự đọc lại sau 30 ngày. Tỷ lệ có thể đã thay đổi sau ngày cập nhật.</p>
      </>}
    </section>
  );
}
