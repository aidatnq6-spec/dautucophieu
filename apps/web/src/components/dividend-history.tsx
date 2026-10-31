"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Year = { year: string; cash: string; stock: string | null; eps_prev: string | null; payout: string | null; stock_note: string | null };
type View = { symbol: string; reason: string | null; years: Year[]; ttm: { cash: string; yield: string | null; price: string | null; since: string };
  avg3: { cash: string; years: string[] } };

const day = (iso: string) => iso.split("-").reverse().join("/");

/** Cash and stock dividends by year, payout against the previous year's EPS, and the trailing twelve-month yield. */
export function DividendHistory({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>(`fairvalue/dividends/${encodeURIComponent(symbol)}`).then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  return (
    <section className="surface" aria-label="Lịch sử cổ tức">
      <h2>Lịch sử cổ tức</h2>
      {message && <p className="errors" role="alert">{message}</p>}
      {view?.reason && <p className="muted">{view.reason}.</p>}
      {view && !view.reason && <>
        <p><strong>12 tháng gần nhất: cổ tức tiền {formatVnd(view.ttm.cash)}/cp</strong>
          {view.ttm.yield && <> · tỷ suất {formatRatio(view.ttm.yield, 1)} trên giá {formatVnd(view.ttm.price)}</>}
          <span className="caption"> (từ {day(view.ttm.since)})</span>
          {" · "}bình quân tiền {view.avg3.years[0]}–{view.avg3.years[view.avg3.years.length - 1]}: {formatVnd(view.avg3.cash)}/cp/năm</p>
        <table className="fv-table" aria-label={`Lịch sử cổ tức ${symbol}`}>
          <thead><tr><th>Năm</th><th className="num">Cổ tức tiền (đ/cp)</th><th className="num">Cổ tức, thưởng cổ phiếu</th><th className="num">EPS năm trước</th>
            <th className="num">Tỷ lệ chi trả</th></tr></thead>
          <tbody>{view.years.map((y) => <tr key={y.year}>
            <td data-label="Năm">{y.year}</td>
            <td data-label="Cổ tức tiền (đ/cp)" className="num">{y.cash === "0" ? "—" : formatVnd(y.cash, { unit: false })}</td>
            <td data-label="Cổ tức, thưởng cổ phiếu" className="num">{y.stock === null ? <span className="caption wrap" title={y.stock_note ?? undefined}>chưa rõ tỷ lệ</span>
              : y.stock === "0" ? "—" : formatRatio(y.stock, 0)}</td>
            <td data-label="EPS năm trước" className="num">{y.eps_prev ? formatVnd(y.eps_prev, { unit: false }) : "—"}</td>
            <td data-label="Tỷ lệ chi trả" className="num">{y.payout ? formatRatio(y.payout, 0) : "—"}</td></tr>)}</tbody>
        </table>
        <p className="caption">Theo năm của ngày giao dịch không hưởng quyền. Tỷ lệ chi trả = cổ tức tiền trong năm / EPS năm tài chính trước (EPS như công bố lúc đó).
          Chỉ tính tỷ suất cho 12 tháng gần nhất: giá lịch sử đã điều chỉnh theo các đợt chia sau đó nên tỷ suất các năm cũ sẽ bị cao lên.</p>
      </>}
    </section>
  );
}
