"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Sign = { key: string; title: string };
export type SignRow = { symbol: string; sector: string | null; signs: Record<string, boolean | null>; count: number; details: Record<string, string> };
type Board = { signs: Sign[]; rows: SignRow[] };

/** One cell: on, off, or not read (missing figures). */
export function cell(v: boolean | null | undefined): { text: string; label: string } {
  return v === true ? { text: "●", label: "có dấu hiệu" } : v === false ? { text: "", label: "không" } : { text: "–", label: "chưa đủ số" };
}

/** Bảng dấu hiệu phải thu: which receivable signs each watched non-financial ticker has on, most first. */
export function ReceivableSigns() {
  const [data, setData] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [all, setAll] = useState(false);
  useEffect(() => { api<Board>("market/receivable-signs").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return null;
  const shown = all ? data.rows : data.rows.filter((r) => r.count > 0);
  return (
    <section className="surface" id="dau-hieu-phai-thu" aria-label="Dấu hiệu phải thu">
      <h2>Dấu hiệu phải thu</h2>
      <p className="caption">Các dấu hiệu về phải thu, trả trước và thu nhập tài chính của từng mã phi tài chính đang theo dõi, gom từ Chất lượng báo cáo (năm gần
        nhất) và khung Phải thu (quý gần nhất). ● có dấu hiệu, – chưa đủ số. Mỗi dấu hiệu là điều nên đọc kỹ thuyết minh, không phải kết luận hay khuyến nghị.</p>
      <p className="caption">{data.rows.filter((r) => r.count > 0).length} / {data.rows.length} mã có ít nhất một dấu hiệu.{" "}
        <button type="button" className="btn text" onClick={() => setAll(!all)}>{all ? "Chỉ hiện mã có dấu hiệu" : "Hiện mọi mã"}</button></p>
      <div className="tablewrap"><table className="fv-table" aria-label="Bảng dấu hiệu phải thu">
        <thead><tr><th>Mã</th><th>Ngành</th>{data.signs.map((s) => <th key={s.key} className="num">{s.title}</th>)}<th className="num">Số dấu hiệu</th></tr></thead>
        <tbody>{shown.map((r) => (
          <tr key={r.symbol}>
            <td data-label="Mã"><Link href={`/research/${r.symbol}`}>{r.symbol}</Link></td>
            <td data-label="Ngành">{r.sector ?? "—"}</td>
            {data.signs.map((s) => { const c = cell(r.signs[s.key]);
              return <td key={s.key} className={`num${r.signs[s.key] ? " negative" : ""}`} data-label={s.title} title={r.details[s.key] ?? c.label} aria-label={`${s.title}: ${c.label}`}>{c.text}</td>; })}
            <td className="num" data-label="Số dấu hiệu"><strong>{r.count}</strong></td>
          </tr>))}
        </tbody>
      </table></div>
      <p className="caption">Đưa chuột vào ● để xem số liệu của dấu hiệu; bấm mã để mở trang mã và đọc khung Phải thu, Chất lượng báo cáo. Báo cáo công khai (VNDirect).</p>
    </section>
  );
}
