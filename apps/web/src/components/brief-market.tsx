"use client";
import { useState } from "react";

type Missing = { status: "missing"; reason: string };
type IndexRow = { id: string; status: "ok"; close: string; change: string; pct: string } | ({ id: string } & Missing);
type Foreign = { buy_volume: number; sell_volume: number; buy_value_bn: string; sell_value_bn: string; net_value_bn: string;
  top_sell: { symbol: string; net_value_bn: string }[]; top_buy: { symbol: string; net_value_bn: string }[] };
type Board = { status: "ok"; value_matched_bn: string; volume_matched: number; breadth: { up: number; down: number; flat: number; no_trade: number };
  foreign: Foreign; sectors: { sector: string; pct: string; count: number }[] } | Missing;
type Hose = { status: "ok"; total_value_bn: string; total_volume: number; foreign: Omit<Foreign, "top_sell" | "top_buy"> } | Missing;
type Ticker = { symbol: string; price: number | null; change: number | null; pct: string | null; held: boolean; sector: string | null;
  state?: "ok" | "no_trade" | "no_price" };
type News = { status: "ok"; items: { title: string; url: string; source: string; published: string; reason: string }[] } | Missing;
export type MarketSection = { session_date: string; updated_at: string; indices: { status: string; rows: IndexRow[] } | Missing; board: Board;
  hose: Hose; proprietary: Missing; tickers: Ticker[]; news: News };

const TOP_TICKERS = 10;
const num = (v: string | number, digits = 2) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const signed = (v: string | number, digits = 2) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${num(Math.abs(Number(v)), digits)}`;
const pct = (v: string) => `${signed(Number(v) * 100)}%`;
const tone = (v: string | number | null) => (v === null || Number(v) === 0 ? "" : Number(v) > 0 ? "positive" : "negative");
const time = (iso: string) => new Date(iso).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });

function Gap({ what, section }: { what: string; section: { reason?: string } }) {
  return <p className="muted">{what}: chưa có số liệu ({section.reason ?? "không rõ lý do"}).</p>;
}

export function BriefMarket({ market, session }: { market: MarketSection | null; session: string }) {
  const [all, setAll] = useState(false);
  const day = `${session.slice(8, 10)}/${session.slice(5, 7)}`;
  if (!market) return (
    <section aria-label="Thị trường phiên"><h2>Thị trường phiên {day}</h2>
      <p className="muted">Chưa có ảnh chụp số liệu thị trường cho phiên này (bản tin lập trước khi có tính năng, hoặc lịch chạy chưa lấy được số).</p></section>);
  const { indices, board, hose, news } = market;
  const tickers = all ? market.tickers : market.tickers.filter((t, i) => t.held || i < TOP_TICKERS);
  return (
    <section aria-label="Thị trường phiên" className="bm">
      <h2>Thị trường phiên {day}</h2>
      <h3>Chỉ số</h3>
      {indices.status === "missing" && "reason" in indices ? <Gap what="Chỉ số" section={indices} /> : (
        <ul className="bm-list">{"rows" in indices && indices.rows.map((r) => r.status === "ok"
          ? <li key={r.id}><strong>{r.id === "VNINDEX" ? "VN-Index" : r.id}</strong> {num(r.close)}{" "}
            <span className={tone(r.change)}>{signed(r.change)} điểm ({pct(r.pct)})</span></li>
          : <li key={r.id}>{r.id === "VNINDEX" ? "VN-Index" : r.id}: chưa có số liệu ({r.reason}).</li>)}</ul>)}
      {board.status === "ok" ? <>
        <h3>Thanh khoản và độ rộng</h3>
        <p>Giá trị khớp lệnh HOSE <strong>{num(board.value_matched_bn)} tỷ đồng</strong> ({num(board.volume_matched, 0)} cp)
          {hose.status === "ok" && <> · HOSE công bố tổng (gồm thỏa thuận) {num(hose.total_value_bn)} tỷ đồng</>}</p>
        <p><span className="positive">{board.breadth.up} tăng</span> · <span className="negative">{board.breadth.down} giảm</span> ·{" "}
          {board.breadth.flat} đứng giá · {board.breadth.no_trade} không giao dịch</p>
        <h3>Khối ngoại</h3>
        <p>Mua {num(board.foreign.buy_volume, 0)} cp / {num(board.foreign.buy_value_bn)} tỷ · Bán {num(board.foreign.sell_volume, 0)} cp /{" "}
          {num(board.foreign.sell_value_bn)} tỷ · Ròng <strong className={tone(board.foreign.net_value_bn)}>{signed(board.foreign.net_value_bn)} tỷ</strong></p>
        {board.foreign.top_sell.length > 0 && <p>Bán ròng mạnh: {board.foreign.top_sell.map((x) => `${x.symbol} ${signed(x.net_value_bn)} tỷ`).join("; ")}</p>}
        {board.foreign.top_buy.length > 0 && <p>Mua ròng mạnh: {board.foreign.top_buy.map((x) => `${x.symbol} ${signed(x.net_value_bn)} tỷ`).join("; ")}</p>}
        {hose.status === "ok" && <p className="caption">HOSE công bố: mua {num(hose.foreign.buy_value_bn)} tỷ · bán {num(hose.foreign.sell_value_bn)} tỷ ·
          ròng {signed(hose.foreign.net_value_bn)} tỷ.</p>}
      </> : <Gap what="Giá trị giao dịch, độ rộng, khối ngoại và ngành" section={board} />}
      <h3>Tự doanh</h3>
      <p className="muted">Chưa có số liệu ({market.proprietary.reason}).</p>
      {board.status === "ok" && board.sectors.length > 0 && <>
        <h3>Ngành (toàn HOSE)</h3>
        <ul className="bm-sectors">{board.sectors.map((s) => <li key={s.sector}><span>{s.sector}</span>{" "}
          <span className={tone(s.pct)}>{pct(s.pct)}</span> <span className="caption">({s.count} mã)</span></li>)}</ul>
      </>}
      <h3>Mã đang theo dõi</h3>
      <ul className="bm-tickers" aria-label="Mã đang theo dõi">{tickers.map((t) => <li key={t.symbol}>
        {t.held ? <strong>{t.symbol}</strong> : t.symbol}{t.held && <span className="pill good">Đang nắm</span>}{" "}
        {t.pct === null ? <span className="muted">{t.state === "no_trade" ? "chưa giao dịch" : "chưa có giá"}</span>
          : <>{num(t.price ?? 0, 0)} <span className={tone(t.change)}>{signed(t.change ?? 0, 0)} ({pct(t.pct)})</span></>}</li>)}</ul>
      {market.tickers.length > tickers.length || all ? <button className="btn" aria-expanded={all} onClick={() => setAll(!all)}>
        {all ? "Thu gọn" : `Xem thêm ${market.tickers.length - tickers.length} mã`}</button> : null}
      <h3>Tin nóng</h3>
      {news.status === "ok" ? (news.items.length ? <ul className="bm-list" aria-label="Tin nóng">{news.items.map((n) => <li key={n.url}>
        <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a> <span className="caption">{n.source} · {time(n.published)} · liên quan: {n.reason}</span>
      </li>)}</ul> : <p className="muted">Không có tin liên quan đến mã đang nắm, mã theo dõi hoặc vĩ mô.</p>) : <Gap what="Tin tức" section={news} />}
      <p className="caption">Số liệu công khai (Vnstock, HOSE, RSS CafeF/Vietstock/Vneconomy); chỉ để theo dõi, không phải khuyến nghị.</p>
    </section>
  );
}
