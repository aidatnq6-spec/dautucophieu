"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Sign = { key: string; title: string };
export type SignRow = { symbol: string; sector: string | null; signs: Record<string, boolean | null>; count: number; details: Record<string, string> };
type Board = { signs: Sign[]; rows: SignRow[] };

/** A ticker's signs that are on, each with its figures, and the ones that could not be read (missing figures). Only the signs its row
 * holds are weighed: a bank's row holds the bank signs alone. */
export function parts(row: SignRow, signs: Sign[]): { on: (Sign & { detail: string | null })[]; missing: string[] } {
  const own = signs.filter((s) => s.key in row.signs);
  return { on: own.filter((s) => row.signs[s.key] === true).map((s) => ({ ...s, detail: row.details[s.key] ?? null })),
    missing: own.filter((s) => row.signs[s.key] == null).map((s) => s.title) };
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
        nhất) và khung Phải thu (quý gần nhất), kèm số liệu của từng dấu hiệu. Ngân hàng chỉ xét dấu hiệu riêng của ngân hàng (lợi nhuận đỡ bởi giảm trích lập), từ báo
        cáo trên VNDirect và nợ nhóm 1–5 trên Vietcap. Mỗi dấu hiệu là điều nên đọc kỹ thuyết minh, không phải kết luận hay khuyến nghị.</p>
      <p className="caption">{data.rows.filter((r) => r.count > 0).length} / {data.rows.length} mã có ít nhất một dấu hiệu.{" "}
        <button type="button" className="btn text" onClick={() => setAll(!all)}>{all ? "Chỉ hiện mã có dấu hiệu" : "Hiện mọi mã"}</button></p>
      <ul className="rs-list" aria-label="Dấu hiệu phải thu theo mã">{shown.map((r) => { const p = parts(r, data.signs);
        return <li key={r.symbol} className="rs-item">
          <div className="rs-head"><Link href={`/research/${r.symbol}`}><strong>{r.symbol}</strong></Link>
            <span className="muted">{r.sector ?? "chưa rõ ngành"}</span>
            <span className={`pill${r.count > 0 ? " bad" : ""}`}>{r.count > 0 ? `${r.count} dấu hiệu` : "không có dấu hiệu"}</span></div>
          {p.on.length > 0 && <ul className="rs-signs">{p.on.map((s) => <li key={s.key}><strong>{s.title}</strong>{s.detail && <>: {s.detail}</>}</li>)}</ul>}
          {p.missing.length > 0 && <p className="caption">Chưa đủ số để xét: {p.missing.join(", ")}.</p>}
        </li>; })}</ul>
      <p className="caption">Bấm mã để mở trang mã và đọc khung Phải thu, Chất lượng báo cáo. Báo cáo công khai (VNDirect; nợ nhóm của ngân hàng từ Vietcap).</p>
    </section>
  );
}
