"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Period = { change: string | null; n: number };
export type ChainReturn = { id: string; name: string; members: number; priced: number; no_data: string[]; stale: string[];
  periods: Record<"w1" | "m1" | "m3" | "y1" | "ytd", Period>; breadth: { up: number; down: number; flat: number };
  position_52w: string | null; leader: { symbol: string; m1: string } | null };

export const PERIODS: ["w1" | "m1" | "m3" | "y1" | "ytd", string][] = [["w1", "1 tuần"], ["m1", "1 tháng"], ["m3", "3 tháng"], ["y1", "1 năm"], ["ytd", "Từ đầu năm"]];
const num = (v: number, d: number) => v.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });

/** A change as a signed percentage with one decimal; "—" when no member has it. */
export function changeText(p: Period): string {
  if (p.change === null) return "—";
  const v = Number(p.change) * 100;
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${num(Math.abs(v), 1)}%`;
}

/** Which members are not counted, and why. */
export function leftOut(c: ChainReturn): string | null {
  const parts = [c.no_data.length ? `chưa có giá: ${c.no_data.join(", ")}` : "", c.stale.length ? `giá cũ: ${c.stale.join(", ")}` : ""].filter(Boolean);
  return parts.length ? parts.join(" · ") : null;
}

/** Hiệu suất theo kỳ: each chain's members over a week to a year, equal-weighted, with today's breadth and the strongest member. */
export function ChainReturns() {
  const [rows, setRows] = useState<ChainReturn[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<{ chains: ChainReturn[] }>("market/value-chains/returns").then((d) => setRows(d.chains),
    (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Hiệu suất theo kỳ">
      <h2>Hiệu suất theo kỳ</h2>
      <p className="caption">Mức thay đổi giá của các mã trong mỗi chuỗi, bình quân đều các mã có số (không trọng số vốn hóa), theo giá đóng cửa đã lưu.
        Vùng 52 tuần là vị trí giữa của các mã giữa đáy và đỉnh năm. Chỉ mô tả dữ liệu, không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!rows && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {rows && <table className="fv-table" aria-label="Hiệu suất chuỗi theo kỳ">
        <thead><tr><th>Chuỗi</th>{PERIODS.map(([, l]) => <th key={l} className="num">{l}</th>)}<th>Hôm nay</th><th className="num">Vùng 52 tuần</th><th>Mạnh nhất 1 tháng</th></tr></thead>
        <tbody>{rows.map((c) => {
          const note = leftOut(c);
          return (
            <tr key={c.id} data-testid={`chain-return-${c.id}`}>
              <td data-label="Chuỗi"><strong>{c.name}</strong> <span className="caption">{c.priced}/{c.members} mã</span>{note && <div className="caption">{note}</div>}</td>
              {PERIODS.map(([k, l]) => <td key={k} data-label={l} className={`num ${c.periods[k].change && Number(c.periods[k].change) > 0 ? "positive" : c.periods[k].change && Number(c.periods[k].change) < 0 ? "negative" : ""}`}>
                {changeText(c.periods[k])}</td>)}
              <td data-label="Hôm nay">{c.breadth.up} tăng · {c.breadth.down} giảm{c.breadth.flat ? ` · ${c.breadth.flat} đứng` : ""}</td>
              <td className="num" data-label="Vùng 52 tuần">{c.position_52w !== null ? `${num(Number(c.position_52w) * 100, 0)}%` : "—"}</td>
              <td data-label="Mạnh nhất 1 tháng">{c.leader ? `${c.leader.symbol} ${changeText({ change: c.leader.m1, n: 1 })}` : "—"}</td>
            </tr>
          );
        })}</tbody>
      </table>}
    </section>
  );
}
