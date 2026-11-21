"use client";
import { useEffect, useMemo, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";

export type FlowRow = { symbol: string; held: boolean; date: string | null; close: string | null; pct: string | null; volume: number | null;
  volume_ratio: string | null; range_position: string | null; foreign_net_bn: string | null; foreign_run: number | null; high_52w: string | null;
  low_52w: string | null; ma20: string | null; ma50: string | null; flags: string[]; missing: string[] };
type Board = { date: string | null; rows: FlowRow[]; counts: Record<string, number>; basis: "closes" };

export const FILTERS: [string, string][] = [["volume_spike", "KL đột biến (≥ 2× TB20)"], ["new_high", "Vượt đỉnh 52 tuần"], ["new_low", "Thủng đáy 52 tuần"],
  ["cross_up_ma20", "Cắt lên MA20"], ["cross_up_ma50", "Cắt lên MA50"], ["cross_down_ma20", "Cắt xuống MA20"], ["cross_down_ma50", "Cắt xuống MA50"],
  ["foreign_buy_5", "Khối ngoại gom ≥ 5 phiên"], ["foreign_sell_5", "Khối ngoại xả ≥ 5 phiên"]];

const num = (v: number, d: number) => v.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (v: string) => { const n = Number(v) * 100; return `${n > 0 ? "+" : n < 0 ? "−" : ""}${num(Math.abs(n), 2)}%`; };

/** Foreign net of the session in tỷ đồng and its run: "+1,5 tỷ · gom 6 phiên". */
export function foreignText(r: FlowRow): string {
  if (r.foreign_net_bn === null) return "—";
  const v = Number(r.foreign_net_bn), run = r.foreign_run ?? 0;
  const side = run > 0 ? `gom ${run} phiên` : run < 0 ? `xả ${-run} phiên` : "";
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${num(Math.abs(v), 1)} tỷ${side ? ` · ${side}` : ""}`;
}

/** Where the close sits between the 52-week low and high, as a share: null when the year is not stored. */
export function yearPosition(r: FlowRow): number | null {
  if (!r.close || !r.high_52w || !r.low_52w) return null;
  const c = Number(r.close), hi = Number(r.high_52w), lo = Number(r.low_52w);
  return hi > lo ? Math.max(0, Math.min(1, (c - lo) / (hi - lo))) : null;
}

/** Dòng tiền & kỹ thuật: the watched tickers' volume, foreign flow and technical crossings on stored data, with quick filters. */
export function FlowBoard() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [only, setOnly] = useState<string | null>(null);
  useEffect(() => { api<Board>("watchlist/flow").then(setBoard, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const rows = useMemo(() => (board?.rows ?? []).filter((r) => !only || r.flags.includes(only)), [board, only]);
  return (
    <section className="surface" aria-label="Dòng tiền và kỹ thuật">
      <h2>Dòng tiền &amp; kỹ thuật</h2>
      <p className="caption">Khối lượng so với trung bình 20 phiên trước, vị trí giá đóng cửa trong biên độ phiên, khối ngoại ròng và số phiên liên tiếp
        cùng chiều. Đỉnh, đáy 52 tuần và MA20, MA50 tính theo giá đóng cửa. Mã thiếu dữ liệu ghi &ldquo;chưa đủ&rdquo;. Chỉ mô tả dữ liệu, không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!board && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {board && <>
        <div className="chips" role="group" aria-label="Lọc nhanh">
          <button type="button" className={`chip${only === null ? " on" : ""}`} aria-pressed={only === null} onClick={() => setOnly(null)}>Tất cả {board.rows.length}</button>
          {FILTERS.map(([id, label]) => <button key={id} type="button" className={`chip${only === id ? " on" : ""}`} aria-pressed={only === id}
            disabled={!board.counts[id]} onClick={() => setOnly(only === id ? null : id)}>{label} {board.counts[id] ?? 0}</button>)}
        </div>
        {board.date && <p className="caption">Phiên {board.date.slice(8, 10)}/{board.date.slice(5, 7)}/{board.date.slice(0, 4)}.</p>}
        {rows.length === 0 ? <p className="muted">Không có mã nào khớp bộ lọc.</p> :
        <table className="fv-table" aria-label="Dòng tiền theo mã">
          <thead><tr><th>Mã</th><th className="num">Giá</th><th className="num">±%</th><th className="num">KL/TB20</th><th>Trong phiên</th>
            <th>Khối ngoại</th><th>Vùng 52 tuần</th><th>Tín hiệu</th></tr></thead>
          <tbody>{rows.map((r) => {
            const y = yearPosition(r);
            return (
              <tr key={r.symbol} data-testid={`flow-${r.symbol}`}>
                <td data-label="Mã"><strong>{r.symbol}</strong>{r.held && <span className="pill good"> đang nắm</span>}</td>
                <td className="num" data-label="Giá">{r.close ? formatVnd(r.close, { unit: false }) : "—"}</td>
                <td className={`num ${r.pct && Number(r.pct) > 0 ? "positive" : r.pct && Number(r.pct) < 0 ? "negative" : ""}`} data-label="±%">{r.pct ? pct(r.pct) : "—"}</td>
                <td className="num" data-label="KL/TB20">{r.volume_ratio ? `${num(Number(r.volume_ratio), 2)}×` : <span className="muted">chưa đủ</span>}</td>
                <td data-label="Trong phiên">{r.range_position !== null ? <span className="fb-range" title={`Đóng cửa ở ${num(Number(r.range_position) * 100, 0)}% biên độ phiên`}>
                  <span style={{ left: `${Number(r.range_position) * 100}%` }} /></span> : <span className="muted">—</span>}</td>
                <td data-label="Khối ngoại">{foreignText(r)}</td>
                <td data-label="Vùng 52 tuần">{y !== null ? <span className="fb-range" title={`Thấp ${formatVnd(r.low_52w!, { unit: false })} · cao ${formatVnd(r.high_52w!, { unit: false })}`}>
                  <span style={{ left: `${y * 100}%` }} /></span> : <span className="muted">chưa đủ</span>}</td>
                <td data-label="Tín hiệu">{r.flags.length ? r.flags.map((f) => FILTERS.find(([id]) => id === f)?.[1] ?? f).join(" · ") : <span className="muted">—</span>}</td>
              </tr>
            );
          })}</tbody>
        </table>}
      </>}
    </section>
  );
}
