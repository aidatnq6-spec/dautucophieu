"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowDownUp, ChartBar } from "lucide-react";
import { ApiError, api } from "../lib/api";

type Format = "money" | "x" | "pct" | "pct2" | "score";
type Column = { key: string; label: string; format: Format; better: "high" | "low" | null; scope: "q" | "year" | "now" };
type PeerRow = { symbol: string; values: Record<string, string | null>; reason?: string | null; top?: number };
type Peers = { symbol: string; sector: string | null; focus: string; reason: string | null; rows: PeerRow[]; kind?: string | null;
  period?: string | null; periods?: string[]; car_year?: string | null; columns?: Column[]; best?: Record<string, string[]>;
  worst?: Record<string, string[]>; median?: Record<string, string>; ranked?: number; price_date?: string | null };

const quarter = (p: string) => `Q${p.slice(-1)}/${p.slice(0, 4)}`;

/** A figure as the ticker's own page writes it: money in tỷ đồng, multiples to two places, percentages to one (two for pct2). */
export function peerCell(v: string | null | undefined, format: Format): string {
  if (v === null || v === undefined) return "—";
  if (format === "score") return v;
  const n = Number(v);
  if (format === "money") return (Math.round(n / 1e9) || 0).toLocaleString("vi-VN");
  if (format === "x") return `${n.toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}x`;
  const places = format === "pct2" ? 2 : 1;
  return `${(n * 100).toLocaleString("vi-VN", { minimumFractionDigits: places, maximumFractionDigits: places })}%`;
}

function numeric(v: string | null | undefined, format: Format): number | null {
  if (v === null || v === undefined) return null;
  if (format === "score") {
    const [a, b] = v.split("/").map(Number);
    return b ? a / b : null;
  }
  return Number(v);
}

/** Rows by one column either way, blanks always last; by ticker when no column is chosen. */
export function sortPeers<T extends { symbol: string; values: Record<string, string | null> }>(rows: T[], key: string | null, format: Format,
  dir: "asc" | "desc"): T[] {
  if (!key) return [...rows].sort((a, b) => a.symbol.localeCompare(b.symbol));
  return [...rows].sort((a, b) => {
    const x = numeric(a.values[key], format), y = numeric(b.values[key], format);
    if (x === null || y === null) return x === null ? (y === null ? a.symbol.localeCompare(b.symbol) : 1) : -1;
    return dir === "asc" ? x - y : y - x;
  });
}

function heading(c: Column, carYear: string | null | undefined): string {
  if (c.scope === "year") return carYear ? `${c.label} ${carYear}` : c.label;
  return c.scope === "now" ? `${c.label} (hiện tại)` : c.label;
}

/** So sánh cùng ngành: every watched ticker of this ticker's sector at one quarter, best and worst of each column marked. */
export function PeerCompare({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Peers | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<string | null>(null);
  const [sort, setSort] = useState<{ key: string | null; dir: "asc" | "desc" }>({ key: null, dir: "asc" });
  const [chart, setChart] = useState<string | null>(null);
  useEffect(() => {
    const path = `fairvalue/peers/${encodeURIComponent(symbol)}${period ? `/${period}` : ""}`;
    api<Peers>(path).then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol, period]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted" role="status">Đang tải so sánh…</p>;
  if (data.reason || !data.columns) return <p className="muted">{data.reason ?? "Chưa có số liệu để so sánh."}</p>;
  const columns = data.columns;
  const format = (key: string | null) => columns.find((c) => c.key === key)?.format ?? "x";
  const rows = sortPeers(data.rows, sort.key, format(sort.key), sort.dir);
  const tone = (key: string, sym: string) => (data.best?.[key]?.includes(sym) ? "positive peer-mark" : data.worst?.[key]?.includes(sym) ? "negative peer-mark" : "");
  const chartColumn = columns.find((c) => c.key === chart) ?? null;
  const bars = chartColumn ? rows.map((r) => ({ symbol: r.symbol, n: numeric(r.values[chartColumn.key], chartColumn.format), v: r.values[chartColumn.key] })) : [];
  const widest = Math.max(1e-12, ...bars.map((b) => Math.abs(b.n ?? 0)));
  function order(key: string, c: Column) {
    // First click puts the better end on top; a second click turns it round.
    const first = c.better === "low" ? "asc" : "desc";
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: first }));
  }
  return (
    <div className="peer">
      <div className="fv-search">
        <label className="field">Kỳ so sánh<select value={data.period ?? ""} onChange={(e) => setPeriod(e.target.value)}>
          {(data.periods ?? []).map((p) => <option key={p} value={p}>{quarter(p)}</option>)}</select></label>
        <p className="caption">{data.rows.length} mã ngành {data.sector} trong danh sách theo dõi · bấm tên cột để sắp xếp, biểu tượng cột để vẽ.</p>
      </div>
      {chartColumn && <figure className="peer-chart" aria-label={`Biểu đồ ${chartColumn.label}`}>
        <figcaption>{heading(chartColumn, data.car_year)}{data.period && chartColumn.scope === "q" ? ` · ${quarter(data.period)}` : ""}
          {" "}<button type="button" className="link-btn" onClick={() => setChart(null)}>Ẩn biểu đồ</button></figcaption>
        {bars.map((b) => <div key={b.symbol} className={`peer-bar-row${b.symbol === data.focus ? " peer-focus" : ""}`}>
          <span>{b.symbol}</span>
          <span className="peer-bar-track">{b.n !== null && <span className={`peer-bar${b.n < 0 ? " neg" : ""}`}
            style={{ width: `${(Math.abs(b.n) / widest) * 100}%` }} />}</span>
          <span className="num">{peerCell(b.v, chartColumn.format)}</span></div>)}
      </figure>}
      <div className="peer-table-wrap">
        <table className="fv-table peer-table" aria-label={`So sánh ngành ${data.sector}${data.period ? `, ${quarter(data.period)}` : ""}`}>
          <thead><tr><th>Mã</th>
            {columns.map((c) => <th key={c.key} className="num" aria-sort={sort.key === c.key ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}>
              <button type="button" className="link-btn" onClick={() => order(c.key, c)}>{heading(c, data.car_year)}
                {sort.key === c.key && <ArrowDownUp size={11} aria-hidden="true" />}</button>
              <button type="button" className="ft-pick" aria-pressed={chart === c.key} aria-label={`Vẽ biểu đồ: ${c.label}`}
                onClick={() => setChart((k) => (k === c.key ? null : c.key))}><ChartBar size={12} aria-hidden="true" /></button></th>)}
            <th className="num">Đứng nhóm đầu</th></tr></thead>
          <tbody>
            {rows.map((r) => <tr key={r.symbol} className={r.symbol === data.focus ? "peer-focus" : undefined}>
              <td data-label="Mã"><Link href={`/research/${r.symbol}`}>{r.symbol}</Link>{r.reason && <span className="caption"> · {r.reason}</span>}</td>
              {columns.map((c) => <td key={c.key} data-label={c.label} className={`num ${tone(c.key, r.symbol)}`}>{peerCell(r.values[c.key], c.format)}</td>)}
              <td data-label="Đứng nhóm đầu" className="num">{r.top ?? 0}/{data.ranked ?? 0}</td>
            </tr>)}
            <tr className="peer-median"><td>Trung vị ngành</td>
              {columns.map((c) => <td key={c.key} className="num">{c.format === "score" ? "" : peerCell(data.median?.[c.key], c.format)}</td>)}<td /></tr>
          </tbody>
        </table>
      </div>
      <p className="caption wrap">
        Số ở {data.period ? quarter(data.period) : "quý gần nhất"}: quý gần nhất mà mọi mã có số liệu đều có (chọn quý khác ở trên); mã chưa có quý đó để trống
        và ghi lý do, không lấy quý khác bù vào. Mỗi số là số đã có ở trang của mã: Bảng số tài chính (P/E, P/B, ROE… tại giá cuối quý, 4 quý gần nhất), chỉ số
        ngành của VNDirect, nợ nhóm 2, CASA và CAR cuối năm từ Vietcap; cột &quot;hiện tại&quot; lấy từ trang Định giá (giá so với giá hợp lý: âm là đang rẻ hơn
        giá hợp lý). P/E và P/B theo giá dùng giá đóng cửa mới nhất đã lưu{data.price_date ? ` (${new Date(data.price_date).toLocaleDateString("vi-VN")})` : ""} : vốn hoá cuối quý mới nhất (giá thực × vốn điều lệ ÷ 10.000 đ) nhân với biến động của giá đã điều chỉnh từ phiên đó, trên LNST công ty mẹ 4 quý và vốn chủ của quý đó; hai cột này có tô màu nhưng không tính vào &quot;Đứng nhóm đầu&quot; để định giá không bị đếm hai lần. Trong mỗi cột, xanh là tốt nhất, đỏ là kém nhất theo chiều của chỉ số (P/E, P/B, nợ xấu thấp là tốt; ROE, CASA, NIM cao là tốt); Vốn hoá
        và LDR không xếp hạng. &quot;Đứng nhóm đầu&quot; đếm số cột mà mã nằm trong 1/3 tốt nhất. Không có điểm tổng: cách cộng các cột là nhận định của
        mỗi người, phần mềm không chọn thay.
      </p>
    </div>
  );
}
