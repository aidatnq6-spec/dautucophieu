"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";

type FromDoc = { truoc: number | null; sau: number | null; so_tep: number; rong: boolean; doc_luc: string | null };
type Deal = { date: string; kind: string | null; shares: number | null; source: string | null; title: string; url: string | null;
  doc_url?: string | null; tu_van_ban?: FromDoc };
type Year = { since: string; bought: number; buy_reports: number; sold: number; sell_reports: number; esop?: number; esop_reports?: number; gift_reports?: number; merged_reports?: number;
  without_volume: number };
type View = { symbol: string; deals: Deal[]; year: Year | null; fetched_at: string | null; stale: boolean; reason: string | null };

const day = (iso: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const shares = (q: number) => formatVnd(String(q), { unit: false });
const KIND: Record<string, [string, string]> = { "Mua": ["Mua", "good"], "Bán": ["Bán", "bad"], "Đăng kí mua": ["Đăng ký mua", ""],
  "Đăng kí bán": ["Đăng ký bán", ""], "ESOP": ["ESOP", ""], "Cho tặng": ["Cho tặng", ""], "Nhận tặng": ["Nhận tặng", ""] };
const FIRST = 15;
const fromDocTitle = (f: FromDoc) => [
  "Đọc từ văn bản HOSE" + (f.so_tep > 1 ? ` (${f.so_tep} tệp, cộng lại)` : ""),
  f.truoc !== null && f.sau !== null ? `trước ${shares(f.truoc)} → sau ${shares(f.sau)} cổ phiếu` : null,
  f.rong ? "số ròng của cả nhóm cổ đông lớn" : null,
].filter(Boolean).join("; ");

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
          {(y.esop_reports ?? 0) > 0 && <>; nhận ESOP <strong>{shares(y.esop ?? 0)}</strong> cổ phiếu ({y.esop_reports} báo cáo, không tính vào mua)</>}
          {(y.gift_reports ?? 0) > 0 && <>; {y.gift_reports} báo cáo cho tặng giữa các cá nhân (không tính vào mua bán)</>}
          {(y.merged_reports ?? 0) > 0 && <>; {y.merged_reports} báo cáo trùng giao dịch đã có (cùng ngày, cùng loại, cùng số) chỉ tính một lần</>}
          {y.without_volume > 0 && <>; {y.without_volume} báo cáo kết quả không ghi loại hoặc khối lượng, xem thông báo gốc</>}.</p>}
        <table className="fv-table" aria-label={`Giao dịch nội bộ ${symbol}`}>
          <thead><tr><th>Ngày</th><th>Loại</th><th className="num">Khối lượng</th><th>Thông báo</th></tr></thead>
          <tbody>{shown.map((d, i) => {
            const [word, tone] = d.kind ? KIND[d.kind] ?? [d.kind, ""] : ["—", ""];
            return <tr key={`${d.date}-${i}`}><td data-label="Ngày">{day(d.date)}</td>
              <td data-label="Loại">{tone ? <span className={`pill ${tone}`}>{word}</span> : word}</td>
              <td data-label="Khối lượng" className="num">{d.shares === null ? "—" : shares(d.shares)}
                {d.tu_van_ban && <span className="muted" title={fromDocTitle(d.tu_van_ban)} aria-label={fromDocTitle(d.tu_van_ban)}> *</span>}</td>
              <td data-label="Thông báo" className="wrap">{d.url ? <a className="wrap" href={d.url} target="_blank" rel="noopener noreferrer">{d.title}</a> : d.title}</td></tr>;
          })}</tbody>
        </table>
        {view.deals.length > FIRST && <div className="actions"><button className="btn" onClick={() => setAll(!all)}>
          {all ? "Thu gọn" : `Hiện tất cả ${view.deals.length} thông báo`}</button></div>}
        {view.deals.some((d) => d.tu_van_ban) && <p className="caption" data-testid="insider-from-doc">* Loại và khối lượng đọc từ văn bản
          đính kèm thông báo HOSE (chữ nhận dạng trên máy), chỉ nhận khi số nắm giữ trước ± số đã giao dịch = số sau; nhóm cổ đông lớn là
          số ròng của cả nhóm. Rê chuột lên dấu * để xem số trước và sau.</p>}
        <p className="caption">Nguồn: thông báo trên HOSE do VNDirect tổng hợp (từ 2024), đọc ngày {day(view.fetched_at)}
          {view.stale ? " — nguồn đang lỗi, đây là bản đã lưu" : ""}; tự đọc lại sau 1 ngày. Loại và khối lượng theo nguồn; &quot;Đăng ký&quot; là ý định,
          chưa phải giao dịch. Gồm cả người có liên quan và cổ đông lớn.</p>
      </>}
    </section>
  );
}
