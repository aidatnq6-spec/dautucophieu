"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

export type CashRow = { symbol: string; sector: string | null; quarter: string | null; cash_like: string | null; debt: string | null; net_cash: string | null;
  close: string | null; close_date: string | null; market_cap: string | null; net_cash_to_cap: string | null; missing: "statements" | "price" | "shares" | null };
type Data = { rows: CashRow[]; cash_rich_from: string };

const ty = (v: string | null) => (v === null ? "—" : `${Math.round(Number(v) / 1e9).toLocaleString("vi-VN")} tỷ`);
const q = (p: string) => `Q${p.slice(-1)}/${p.slice(0, 4)}`;
const MISSING = { statements: "thiếu tiền, đầu tư ngắn hạn hoặc nợ vay trong báo cáo", price: "chưa có giá", shares: "chưa có số cổ phiếu lưu hành" };

/** Net cash against market value as a percent, or why it is blank. */
export function ratioText(r: CashRow): string {
  if (r.net_cash_to_cap === null) return r.missing ? MISSING[r.missing] : "—";
  return `${(Number(r.net_cash_to_cap) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

/** Kho tiền: the watched non-financial tickers by net cash against their market value, highest first. */
export function CashRanking() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Data>("market/cash-ranking").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return null;
  const rich = Number(data.cash_rich_from);
  return (
    <section className="surface" id="kho-tien" aria-label="Kho tiền">
      <h2>Kho tiền</h2>
      <p className="caption">Tiền ròng = tiền + đầu tư tài chính ngắn hạn − nợ vay, quý gần nhất; so với vốn hóa = giá đóng cửa gần nhất × cổ phiếu lưu hành.
        Tỷ lệ cao nghĩa là một phần lớn giá cổ phiếu là tiền doanh nghiệp đang giữ; từ {Math.round(rich * 100)}% được ghi là kho tiền lớn (lãi suất tiền gửi tăng
        thì nhóm này thu lãi nhiều hơn). Không gồm ngân hàng, chứng khoán, bảo hiểm.</p>
      {data.rows.length === 0 ? <p className="muted">Chưa có mã phi tài chính nào trong danh sách theo dõi.</p> : <div className="tablewrap">
        <table className="fv-table" aria-label="Xếp hạng kho tiền">
          <thead><tr><th>Mã</th><th>Ngành</th><th>Quý</th><th className="num">Tiền + đầu tư ngắn hạn</th><th className="num">Nợ vay</th>
            <th className="num">Tiền ròng</th><th className="num">Vốn hóa</th><th className="num">Tiền ròng / vốn hóa</th></tr></thead>
          <tbody>{data.rows.map((r) => (
            <tr key={r.symbol}>
              <td data-label="Mã"><Link href={`/research/${r.symbol}`}>{r.symbol}</Link>
                {r.net_cash_to_cap !== null && Number(r.net_cash_to_cap) >= rich && <> <span className="pill good">Kho tiền lớn</span></>}</td>
              <td data-label="Ngành">{r.sector ?? "—"}</td>
              <td data-label="Quý">{r.quarter ? q(r.quarter) : "—"}</td>
              <td className="num" data-label="Tiền + đầu tư ngắn hạn">{ty(r.cash_like)}</td>
              <td className="num" data-label="Nợ vay">{ty(r.debt)}</td>
              <td className={`num${r.net_cash !== null && Number(r.net_cash) < 0 ? " negative" : ""}`} data-label="Tiền ròng">{ty(r.net_cash)}</td>
              <td className="num" data-label="Vốn hóa">{ty(r.market_cap)}</td>
              <td className={`num${r.net_cash_to_cap === null ? " muted" : ""}`} data-label="Tiền ròng / vốn hóa">{ratioText(r)}</td>
            </tr>))}
          </tbody>
        </table>
      </div>}
      <p className="caption">Báo cáo công khai (VNDirect) và giá đóng cửa đã lưu; ô thiếu số để trống kèm lý do. Không phải khuyến nghị.</p>
    </section>
  );
}
