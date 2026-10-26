"use client";
import { useEffect, useMemo, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Row = { ticker: string; groups: string[]; held: boolean; close: string | null; date: string | null;
  change_1d: string | null; change_20d: string | null; stale: boolean };
type Watchlist = { provenance: string; groups_as_of: string | null; rows: Row[] };

const FILTERS = [{ id: "all", label: "Tất cả" }, { id: "VN30", label: "VN30" }, { id: "VN100", label: "VN100" }, { id: "held", label: "Đang nắm" }];
const SORTS = [{ id: "ticker", label: "Mã (A–Z)" }, { id: "change_1d", label: "Thay đổi trong phiên" }, { id: "change_20d", label: "Thay đổi 20 phiên" }] as const;
type SortId = (typeof SORTS)[number]["id"];

export function Change({ value }: { value: string | null }) {
  if (value === null) return <>—</>;
  const down = value.startsWith("-");
  return <span className={down ? "negative" : "positive"}>{down ? "" : "+"}{formatRatio(value, 2)}</span>;
}

export function WatchlistView() {
  const [data, setData] = useState<Watchlist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState<SortId>("ticker");
  useEffect(() => { api<Watchlist>("watchlist").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const rows = useMemo(() => {
    const kept = (data?.rows ?? []).filter((r) => filter === "all" || (filter === "held" ? r.held : r.groups.includes(filter)));
    if (sort === "ticker") return kept;
    // Strings from the API are fixed four-place ratios, so Number() is only used to order them; missing values go last.
    return [...kept].sort((a, b) => (b[sort] === null ? -1 : a[sort] === null ? 1 : Number(b[sort]) - Number(a[sort])));
  }, [data, filter, sort]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  if (!data.rows.length) return <p className="muted">Chưa có mã nào trong data\market-symbols.txt.</p>;
  return (
    <section className="surface">
      <p className="notice">Chỉ là dữ liệu giá ({data.provenance === "vnstock_adjusted" ? "Vnstock, giá đã điều chỉnh" : data.provenance}), không phải khuyến nghị mua bán.
        Mã chỉ được nghiên cứu để mua khi có dữ liệu 10 năm đã kiểm chứng.</p>
      <div className="actions" role="radiogroup" aria-label="Lọc theo nhóm">
        {FILTERS.map((f) => <label key={f.id} className="choice"><input type="radio" name="filter" checked={filter === f.id} onChange={() => setFilter(f.id)} />{f.label}</label>)}
        <label className="field">Sắp xếp<select value={sort} onChange={(e) => setSort(e.target.value as SortId)}>
          {SORTS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
      </div>
      <div className="tablewrap">
        <table aria-label="Danh sách theo dõi">
          <thead><tr><th>Mã</th><th>Nhóm</th><th className="num">Giá đóng cửa (đ/cp)</th><th className="num">Trong phiên</th><th className="num">20 phiên</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.ticker}>
              <td><strong>{r.ticker}</strong>{r.held && <> <span className="pill good">Đang nắm</span></>}</td>
              <td>{r.groups.join(", ") || "—"}</td>
              <td className="num">{r.close ? <>{formatVnd(r.close, { unit: false })} <span className="caption">({r.date}{r.stale ? ", giá cũ" : ""})</span></> : "Chưa có giá"}</td>
              <td className="num"><Change value={r.change_1d} /></td>
              <td className="num"><Change value={r.change_20d} /></td>
            </tr>))}
          </tbody>
        </table>
      </div>
      {data.groups_as_of && <p className="caption">Thành phần VN30/VN100 theo nguồn ngày {data.groups_as_of}.</p>}
    </section>
  );
}
