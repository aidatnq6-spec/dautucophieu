"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal } from "../lib/format";
import { Change } from "./watchlist-view";

type Index = { entity_id: string; close: string; date: string; change_1d: string | null; change_20d: string | null; ma20: string | null; above_ma20: boolean | null };
type Breadth = { up: number; down: number; flat: number; missing: number };
type Sector = Breadth & { sector: string; count: number; tickers: string[]; avg_1d: string | null; avg_20d: string | null;
  best: string | null; worst: string | null; held: string[] };
type Overview = { provenance: string; index: Index | null; breadth: Breadth; sectors: Sector[]; sectors_as_of: string | null;
  macro: { available: boolean; reason: string } };

export function MarketView() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Overview>("market/overview").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted">Đang tải…</p>;
  const { index: ix, breadth: b } = data;
  return (
    <>
      <p className="notice">Chỉ tổng hợp từ dữ liệu giá ({data.provenance === "vnstock_adjusted" ? "Vnstock, giá đã điều chỉnh" : data.provenance}),
        không phải khuyến nghị mua bán.</p>
      <section className="surface" aria-label="Thị trường chung">
        <h2>Thị trường chung</h2>
        {ix ? <p><strong>VN-Index {formatDecimal(ix.close, 2)}</strong> điểm ({ix.date}) · trong phiên <Change value={ix.change_1d} /> · 20 phiên <Change value={ix.change_20d} />
          {ix.ma20 && <> · {ix.above_ma20 ? "trên" : "dưới"} đường trung bình 20 phiên ({formatDecimal(ix.ma20, 2)})</>}</p>
          : <p className="muted">Chưa có dữ liệu VN-Index.</p>}
        <p>Trong {b.up + b.down + b.flat + b.missing} mã đang theo dõi: {b.up} mã tăng, {b.down} mã giảm, {b.flat} mã đứng giá
          {b.missing ? `, ${b.missing} mã chưa có giá` : ""}.</p>
      </section>
      <section className="surface">
        <h2>Diễn biến theo ngành</h2>
        <p className="caption">Trung bình cộng các mã đang theo dõi trong ngành (không theo vốn hóa), xếp theo mức thay đổi 20 phiên.</p>
        <div className="tablewrap">
          <table aria-label="Diễn biến theo ngành">
            <thead><tr><th>Ngành</th><th className="num">Số mã</th><th className="num">Trong phiên</th><th className="num">20 phiên</th>
              <th>Tăng / giảm</th><th>Mạnh nhất / yếu nhất (20 phiên)</th></tr></thead>
            <tbody>{data.sectors.map((s) => (
              <tr key={s.sector}>
                <td><strong>{s.sector}</strong>{s.held.length > 0 && <> <span className="pill good">Đang nắm: {s.held.join(", ")}</span></>}</td>
                <td className="num">{s.count}</td>
                <td className="num"><Change value={s.avg_1d} /></td>
                <td className="num"><Change value={s.avg_20d} /></td>
                <td>{s.up} / {s.down}</td>
                <td>{s.best ? `${s.best} / ${s.worst}` : "—"}</td>
              </tr>))}
            </tbody>
          </table>
        </div>
        {data.sectors_as_of && <p className="caption">Phân ngành ICB cấp 2 theo nguồn ngày {data.sectors_as_of}.</p>}
      </section>
      <section className="surface" aria-label="Vĩ mô">
        <h2>Vĩ mô</h2>
        <p className="muted">Chưa có dữ liệu vĩ mô: GDP, CPI, lãi suất, cung tiền, FDI và xuất nhập khẩu không có trong gói Vnstock miễn phí.
          Ứng dụng không ước đoán thay. Cần nguồn trả phí hoặc số liệu bạn tự nhập từ Tổng cục Thống kê và Ngân hàng Nhà nước.</p>
      </section>
    </>
  );
}
