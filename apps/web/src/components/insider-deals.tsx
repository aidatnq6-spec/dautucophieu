"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";

type Deal = { date: string; kind: string | null; shares: number | null; source: string | null; title: string; url: string | null };
type Year = { since: string; bought: number; buy_reports: number; sold: number; sell_reports: number; without_volume: number };
type View = { symbol: string; deals: Deal[]; year: Year | null; fetched_at: string | null; stale: boolean; reason: string | null };

const day = (iso: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const shares = (q: number) => formatVnd(String(q), { unit: false });
const KIND: Record<string, [string, string]> = { "Mua": ["Mua", "good"], "Bán": ["Bán", "bad"], "Đăng kí mua": ["Đăng ký mua", ""],
  "Đăng kí bán": ["Đăng ký bán", ""] };
const FIRST = 15;

/** Insider and major-shareholder trade notices published on HOSE (via VNDirect), newest first, with a 12-month tally of done trades. */
export function InsiderDeals({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [all, setAll] = useState(false);
  useEffect(() => {
    api<View>(`fairvalue/insider/${encodeURIComponent(symbol)}`).then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  const y = view?.year;
  const shown = all ? view?.deals ?? [] : (view?.deals ?? []).slice(0, FIRST);
  return (
    <section className="surface" aria-label="Giao dịch nội bộ và cổ đông lớn">
      <h2>Giao dịch nội bộ và cổ đông lớn</h2>
      {!view && !message && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {message && <p className="errors" role="alert">{message}</p>}
      {view?.reason && <p className="muted">{view.reason}.</p>}
      {view && !view.reason && !view.deals.length && <p className="muted">Nguồn chưa có thông báo giao dịch nào của {symbol}.</p>}
      {view && !view.reason && view.deals.length > 0 && <>
        {y && <p data-testid="insider-year">12 tháng từ {day(y.since)}: đã mua <strong>{shares(y.bought)}</strong> cổ phiếu ({y.buy_reports} báo cáo),
          đã bán <strong>{shares(y.sold)}</strong> cổ phiếu ({y.sell_reports} báo cáo)
          {y.without_volume > 0 && <>; {y.without_volume} báo cáo kết quả không ghi loại hoặc khối lượng, xem thông báo gốc</>}.</p>}
        <table className="fv-table" aria-label={`Giao dịch nội bộ ${symbol}`}>
          <thead><tr><th>Ngày</th><th>Loại</th><th className="num">Khối lượng</th><th>Thông báo</th></tr></thead>
          <tbody>{shown.map((d, i) => {
            const [word, tone] = d.kind ? KIND[d.kind] ?? [d.kind, ""] : ["—", ""];
            return <tr key={`${d.date}-${i}`}><td data-label="Ngày">{day(d.date)}</td>
              <td data-label="Loại">{tone ? <span className={`pill ${tone}`}>{word}</span> : word}</td>
              <td data-label="Khối lượng" className="num">{d.shares === null ? "—" : shares(d.shares)}</td>
              <td data-label="Thông báo" className="wrap">{d.url ? <a className="wrap" href={d.url} target="_blank" rel="noopener noreferrer">{d.title}</a> : d.title}</td></tr>;
          })}</tbody>
        </table>
        {view.deals.length > FIRST && <div className="actions"><button className="btn" onClick={() => setAll(!all)}>
          {all ? "Thu gọn" : `Hiện tất cả ${view.deals.length} thông báo`}</button></div>}
        <p className="caption">Nguồn: thông báo trên HOSE do VNDirect tổng hợp (từ 2024), đọc ngày {day(view.fetched_at)}
          {view.stale ? " — nguồn đang lỗi, đây là bản đã lưu" : ""}; tự đọc lại sau 1 ngày. Loại và khối lượng theo nguồn; &quot;Đăng ký&quot; là ý định,
          chưa phải giao dịch. Gồm cả người có liên quan và cổ đông lớn.</p>
      </>}
    </section>
  );
}
