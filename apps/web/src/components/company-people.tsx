"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Holder = { name: string; type: string | null; quantity: number | null; percent: number | null; updated: string | null };
type Officer = { name: string; position: string | null; percent: number | null; quantity: number | null };
type Stakes = { foreign: string | null; foreign_max: string | null; state: string | null; free_float: string | null };
type OwnerType = { type: string; percent: string | null; shares: number | null; updated: string | null };
type View = { symbol: string; shareholders: Holder[]; officers: Officer[]; ownership: Stakes | null; structure: OwnerType[] | null;
  others_percent: string | null; fetched_at: string | null; stale: boolean; reason: string | null };

const TYPE: Record<string, string> = { Individual: "Cá nhân", Organization: "Tổ chức" };
const day = (iso: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const share = (p: number | null) => (p === null ? "—" : formatRatio(String(p), 2));
const shares = (q: number | null) => (q === null ? "—" : formatVnd(String(q), { unit: false }));
const TOP = 10;
const stake = (v: string | null) => (v === null ? "chưa có số" : formatRatio(v, 2));
// Same person on both lists: exact name after trimming and case folding; anything looser would be a guess.
const key = (name: string) => name.trim().replace(/\s+/g, " ").toLocaleLowerCase("vi");

/** Foreign/state stakes, holdings by owner type, major shareholders (top ten by stake, the rest as "Khác", officers' roles beside them) and officers, from the company's public disclosures (Vnstock, VCI), cached a month. */
export function CompanyPeople({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>(`fairvalue/people/${encodeURIComponent(symbol)}`).then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  const holders = [...(view?.shareholders ?? [])].sort((a, b) => (b.percent ?? -1) - (a.percent ?? -1)).slice(0, TOP);
  const roles = new Map<string, string>();
  for (const o of view?.officers ?? []) if (o.position && !roles.has(key(o.name))) roles.set(key(o.name), o.position);
  const own = view?.ownership;
  return (
    <section className="surface" aria-label="Cổ đông lớn và ban lãnh đạo">
      <h2>Cổ đông lớn và ban lãnh đạo</h2>
      {!view && !message && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {message && <p className="errors" role="alert">{message}</p>}
      {view?.reason && <p className="muted">{view.reason}.</p>}
      {view && !view.reason && <>
        <h3>Cơ cấu sở hữu</h3>
        {own ? <p>Nước ngoài <strong>{stake(own.foreign)}</strong> (room tối đa {stake(own.foreign_max)}) · Nhà nước <strong>{stake(own.state)}</strong>
          {" "}· Tự do chuyển nhượng {stake(own.free_float)} <span className="caption">(VCI, số hiện tại)</span></p>
          : <p className="muted">Chưa đọc được tỷ lệ sở hữu nước ngoài và nhà nước (nguồn VCI lỗi).</p>}
        {view.structure?.length ? <table className="fv-table" aria-label={`Cơ cấu sở hữu ${symbol}`}>
          <thead><tr><th>Nhóm cổ đông</th><th className="num">Tỷ lệ</th><th className="num">Số cổ phiếu</th><th>Ngày</th></tr></thead>
          <tbody>{view.structure.map((t) => <tr key={t.type}><td data-label="Nhóm cổ đông">{t.type}</td>
            <td data-label="Tỷ lệ" className="num">{t.percent === null ? "—" : formatRatio(t.percent, 2)}</td>
            <td data-label="Số cổ phiếu" className="num">{shares(t.shares)}</td><td data-label="Ngày">{day(t.updated)}</td></tr>)}</tbody>
        </table> : <p className="muted">Chưa đọc được cơ cấu theo nhóm cổ đông (nguồn KBS lỗi hoặc không có số).</p>}
        <h3>{Math.min(TOP, view.shareholders.length)} cổ đông lớn nhất</h3>
        <table className="fv-table" aria-label={`Cổ đông lớn ${symbol}`}>
          <thead><tr><th>Cổ đông</th><th>Chức vụ</th><th>Loại</th><th className="num">Tỷ lệ</th><th className="num">Số cổ phiếu</th><th>Cập nhật</th></tr></thead>
          <tbody>{holders.map((h) => <tr key={h.name}><td data-label="Cổ đông">{h.name}</td>
            <td data-label="Chức vụ">{roles.get(key(h.name)) ?? ""}</td><td data-label="Loại">{TYPE[h.type ?? ""] ?? h.type ?? "—"}</td>
            <td data-label="Tỷ lệ" className="num">{share(h.percent)}</td><td data-label="Số cổ phiếu" className="num">{shares(h.quantity)}</td>
            <td data-label="Cập nhật">{day(h.updated)}</td></tr>)}</tbody>
          <tfoot><tr><td data-label="Cổ đông">Khác</td><td /><td /><td data-label="Tỷ lệ" className="num">
            {view.others_percent === null ? <span title="Một trong các cổ đông lớn không có tỷ lệ">—</span> : formatRatio(view.others_percent, 2)}</td>
            <td /><td /></tr></tfoot>
        </table>
        <h3>Ban lãnh đạo</h3>
        <table className="fv-table" aria-label={`Ban lãnh đạo ${symbol}`}>
          <thead><tr><th>Họ tên</th><th>Chức vụ</th><th className="num">Tỷ lệ sở hữu</th><th className="num">Số cổ phiếu</th></tr></thead>
          <tbody>{view.officers.map((o) => <tr key={`${o.name}-${o.position}`}><td data-label="Họ tên">{o.name}</td><td data-label="Chức vụ">{o.position ?? "—"}</td>
            <td data-label="Tỷ lệ sở hữu" className="num">{share(o.percent)}</td><td data-label="Số cổ phiếu" className="num">{shares(o.quantity)}</td></tr>)}</tbody>
        </table>
        <p className="caption">Nguồn: công bố của doanh nghiệp qua Vnstock (VCI; nhóm cổ đông từ KBS), đọc ngày {day(view.fetched_at)}{view.stale ? " — nguồn đang lỗi, đây là bản đã lưu" : ""};
          tự đọc lại sau 30 ngày. Tỷ lệ có thể đã thay đổi sau ngày cập nhật.</p>
      </>}
    </section>
  );
}
