"use client";
import { useState } from "react";
import { RecentSignals, type SignalRow } from "./recent-signals";
import { HeatMapView, ImpactView, type HeatMap, type Impact } from "./session-maps";

type Missing = { status: "missing"; reason: string };
type IndexRow = { id: string; status: "ok"; close: string; change: string; pct: string } | ({ id: string } & Missing);
type Foreign = { buy_volume: number; sell_volume: number; buy_value_bn: string; sell_value_bn: string; net_value_bn: string;
  top_sell: { symbol: string; net_value_bn: string }[]; top_buy: { symbol: string; net_value_bn: string }[] };
type Board = { status: "ok"; value_matched_bn: string; volume_matched: number; breadth: { up: number; down: number; flat: number; no_trade: number };
  foreign: Foreign | null; foreign_missing?: string; sectors: { sector: string; pct: string; count: number }[]; spread?: Spread } | Missing;
type Proprietary = { status: "ok"; source: string; date: string; lag_sessions: number; buy_volume: number; sell_volume: number;
  buy_value_bn: string; sell_value_bn: string; net_value_bn: string; top_sell: { symbol: string; net_value_bn: string }[] | null;
  top_buy: { symbol: string; net_value_bn: string }[] | null; top_reason?: string } | Missing;
// Khối ngoại và tự doanh ròng 20 phiên (27/11/2026): each ends at its own newest session, a missing session is a null bar
type FlowBar = { date: string; net_bn: string | null };
type Flow = { status: "ok"; date: string; lag_sessions: number; net_bn: string; sum_bn: string; missing: number; bars: FlowBar[] } | Missing;
type Spread = { count: number; mean_pct: string | null; median_pct: string | null };
type Hose = { status: "ok"; total_value_bn: string; total_volume: number; foreign: Omit<Foreign, "top_sell" | "top_buy"> } | Missing;
type Ticker = { symbol: string; price: number | null; change: number | null; pct: string | null; held: boolean; sector: string | null;
  state?: "ok" | "no_trade" | "no_price" };
type News = { status: "ok"; items: { title: string; url: string; source: string; published: string; reason: string }[] } | Missing;
type Streak = { direction: "up" | "down" | "flat" | null; sessions: number; at_least: boolean; change: string | null; pct: string | null };
type Volume = { status: "ok"; today: number; previous: number; change_pct: string | null; avg20: number; ratio20: string | null } | Missing;
type IndexSession = { status: "ok"; range: { high: string; low: string; close: string; from_high: string; from_low: string }; streak: Streak;
  volume: Volume } | Missing;
type HoseLiquidity = { status: "ok"; today_bn: string; previous_bn: string; change_pct: string; avg20_bn: string; ratio20: string; avg_sessions?: number;
  previous_session?: string; previous_skipped?: boolean } | Missing;
export type MarketSection = { session_date: string; updated_at: string; indices: { status: string; rows: IndexRow[] } | Missing; board: Board;
  hose: Hose; proprietary: Proprietary; tickers: Ticker[]; news: News; index_session?: IndexSession; hose_liquidity?: HoseLiquidity;
  recovery?: Recovery; signal_lines?: string[]; asia_line?: string | null; us_line?: string | null; shock_line?: string | null; recent_signals?: SignalRow[]; impact?: Impact; heatmap?: HeatMap;
  flows?: { foreign: Flow; proprietary: Flow } };
type Check = { id: string; met: boolean | null; label: string; figure: string };
type Recovery = { status: "ok"; met: number; known: number; total: number; checks: Check[] } | Missing;

const TOP_TICKERS = 10;
const num = (v: string | number, digits = 2) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const signed = (v: string | number, digits = 2) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${num(Math.abs(Number(v)), digits)}`;
const pct = (v: string) => `${signed(Number(v) * 100)}%`;
const tone = (v: string | number | null) => (v === null || Number(v) === 0 ? "" : Number(v) > 0 ? "positive" : "negative");
const time = (iso: string) => new Date(iso).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });

/** The run of sessions in words; a run reaching past the stored bars gets no total, a run that cannot be read gets nothing. */
export function streakText(k: Streak): string | null {
  if (k.direction === null) return null;
  if (k.direction === "flat") return "Đứng giá so với phiên trước";
  const word = k.direction === "up" ? "Tăng" : "Giảm";
  if (k.at_least || k.change === null || k.pct === null) return `${word} ít nhất ${k.sessions} phiên liên tiếp`;
  return `${word} ${k.sessions} phiên liên tiếp, ${signed(k.change)} điểm (${pct(k.pct)})`;
}

/** Lan tỏa: every traded stock at the same weight beside the cap-weighted VN-Index; an opposite direction is named, nothing more. */
export function spreadText(s: Spread, vnPct: string | null): string | null {
  if (s.mean_pct === null || s.median_pct === null) return null;
  const head = `Trung bình cộng các mã ${pct(s.mean_pct)}, trung vị ${pct(s.median_pct)} (${s.count} mã có giao dịch)`;
  if (vnPct === null) return head;
  return `${head}; VN-Index ${pct(vnPct)}${Number(vnPct) * Number(s.mean_pct) < 0 ? ", ngược chiều" : ""}`;
}

/** Tự doanh's heading: VNDirect posts some sessions late, so a session other than the brief's is named with its lag. */
export function proprietaryHead(p: { date: string; lag_sessions: number }): string {
  if (!p.lag_sessions) return "Tự doanh";
  const [y, m, d] = p.date.split("-");
  return `Tự doanh — phiên ${d}/${m}/${y} (VNDirect chậm ${p.lag_sessions} phiên)`;
}

/** Khối ngoại with no figures (VNDirect served every stock at 0, 27/11/2026): the reason, never a zero; null when there are figures. */
export function foreignGap(b: { foreign: unknown; foreign_missing?: string }): string | null {
  return b.foreign ? null : `Chưa có số liệu (${b.foreign_missing ?? "không rõ lý do"}).`;
}

/** A flow row's figure and caption: its own session (with the lag when VNDirect is late), the 20 sessions' sum, missing sessions. */
export function flowHead(f: { date: string; lag_sessions: number; net_bn: string; sum_bn: string; missing: number }): { value: string; tone: string; sub: string } {
  const [, m, d] = f.date.split("-");
  return { value: `${signed(f.net_bn, 1)} tỷ`, tone: tone(f.net_bn),
    sub: `Phiên ${d}/${m}${f.lag_sessions ? ` (chậm ${f.lag_sessions} phiên)` : ""} · 20 phiên ${signed(f.sum_bn, 0)} tỷ${f.missing ? ` (thiếu ${f.missing} phiên)` : ""}` };
}

/** Bars from a middle line, one scale for the row; a missing session is no bar (null), never a zero bar. */
export function barHeights(bars: FlowBar[], height: number): ({ y: number; h: number; tone: string } | null)[] {
  const mid = height / 2;
  const top = Math.max(0, ...bars.map((b) => (b.net_bn === null ? 0 : Math.abs(Number(b.net_bn)))));
  return bars.map((b) => {
    if (b.net_bn === null) return null;
    const v = Number(b.net_bn), h = top ? Math.round((Math.abs(v) / top) * mid * 100) / 100 : 0;
    return { y: v > 0 ? mid - h : mid, h, tone: tone(v) };
  });
}

/** One bar read out: its date and net, or that the session has no figures (hover, tap and screen readers). */
export function barLabel(b: FlowBar): string {
  const day = b.date.split("-").reverse().join("/");
  return b.net_bn === null ? `${day}: thiếu số` : `${day}: ${signed(b.net_bn, 1)} tỷ`;
}

function FlowRows({ flows }: { flows: { foreign: Flow; proprietary: Flow } }) {
  return <div className="bm-flows">
    <FlowRow label="Khối ngoại ròng" f={flows.foreign} />
    <FlowRow label="Tự doanh ròng" f={flows.proprietary} />
  </div>;
}

function FlowRow({ label, f }: { label: string; f: Flow }) {
  const [picked, setPicked] = useState<number | null>(null);
  const H = 28, W = 6;
  if (f.status !== "ok") return <div className="bm-flow"><div><strong>{label}</strong><div className="caption">{f.reason}</div></div></div>;
  const head = flowHead(f);
  return <div className="bm-flow">
    <div><strong>{label}</strong><div className="caption">{head.sub}</div>
      {picked !== null && f.bars[picked] && <div className="caption" data-testid="flow-picked">{barLabel(f.bars[picked])}</div>}</div>
    <strong className={`bm-flow-value ${head.tone}`}>{head.value}</strong>
    <svg className="bm-flow-bars" width={f.bars.length * W} height={H} aria-hidden="true">
      <line x1={0} x2={f.bars.length * W} y1={H / 2} y2={H / 2} className="bm-flow-axis" />
      {barHeights(f.bars, H).map((b, i) => b && <rect key={`b${f.bars[i].date}`} x={i * W + 1} y={b.y} width={W - 2} height={Math.max(b.h, 0.5)}
        className={`bm-bar ${b.tone}${picked === i ? " picked" : ""}`} />)}
      {f.bars.map((bar, i) => <rect key={`t${bar.date}`} x={i * W} y={0} width={W} height={H} className="bm-bar-hit"
        onClick={() => setPicked(picked === i ? null : i)}><title>{barLabel(bar)}</title></rect>)}
    </svg>
    <ul className="visually-hidden" aria-label={`${label}, ${f.bars.length} phiên`}>{f.bars.map((bar) => <li key={bar.date}>{barLabel(bar)}</li>)}</ul>
  </div>;
}

/** Bảng kiểm "Thị trường phục hồi": how many conditions are met, and how many have no figures (counted neither way). */
export function recoveryHead(r: { met: number; known: number; total: number }): string {
  const unknown = r.total - r.known;
  return `${r.met}/${r.total} điều kiện đạt${unknown ? `, ${unknown} điều kiện chưa có số` : ""}`;
}

/** A figure against the previous session and the 20 before it. */
export function baseText(f: { change_pct: string | null; ratio20: string | null; avg_sessions?: number; previous_session?: string; previous_skipped?: boolean }): string {
  // HOSE's value (fix 25/11/2026): the previous session with a figure and the sessions with one, named when they differ
  const previous = f.previous_skipped && f.previous_session ? `phiên ${f.previous_session.slice(8, 10)}/${f.previous_session.slice(5, 7)}` : "phiên trước";
  const n = f.avg_sessions ?? 20;
  return [f.change_pct !== null ? `${pct(f.change_pct)} so với ${previous}` : null,
    f.ratio20 !== null ? `bằng ${num(f.ratio20)} lần trung bình ${n} phiên${n !== 20 ? " có số" : ""}` : null].filter(Boolean).join(" · ");
}

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
  const shape = market.index_session, liquidity = market.hose_liquidity;
  const vn = "rows" in indices ? indices.rows.find((r) => r.id === "VNINDEX") : undefined;
  const vnPct = vn && vn.status === "ok" ? vn.pct : null;
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
      {shape && (shape.status === "ok" ? <>
        <p data-testid="index-range">Trong phiên: cao {num(shape.range.high)} · thấp {num(shape.range.low)} · đóng cửa cách đỉnh{" "}
          <strong>{num(shape.range.from_high)} điểm</strong>, cách đáy {num(shape.range.from_low)} điểm</p>
        {streakText(shape.streak) && <p data-testid="index-streak">Chuỗi: {streakText(shape.streak)}</p>}
        <p data-testid="index-volume">Khối lượng khớp lệnh: {shape.volume.status === "ok"
          ? <>{num(shape.volume.today, 0)} cp · {baseText(shape.volume)} <span className="caption">(trung bình {num(shape.volume.avg20, 0)} cp)</span></>
          : <span className="muted">chưa có số liệu ({shape.volume.reason})</span>}</p>
        <p className="caption">Nến ngày VN-Index theo KBS (vnstock); cao/thấp có thể gồm mức tham chiếu đầu phiên.</p>
      </> : <Gap what="Trong phiên" section={shape} />)}
      {market.asia_line && <p data-testid="asia-line">{market.asia_line}</p>}
      {market.us_line && <p data-testid="us-line">{market.us_line}</p>}
      {market.shock_line && <p data-testid="shock-line"><strong>{market.shock_line}</strong></p>}
      {(market.signal_lines?.length ?? 0) > 0 && <section aria-label="Tín hiệu phiên" data-testid="signals">
        <h3>Tín hiệu phiên</h3>
        <ul className="bm-list">{market.signal_lines!.map((s) => <li key={s}>{s}</li>)}</ul>
        <p className="caption">Điểm kéo chỉ số tính theo số cổ phiếu lưu hành (VNDirect) và giá cuối phiên; chỉ hiện khi tổng khớp mức thay đổi
          của VN-Index. Thanh khoản so với trung bình 20 phiên.</p>
      </section>}
      <ImpactView impact={market.impact} />
      <HeatMapView heatmap={market.heatmap} />
      {market.recent_signals && <RecentSignals rows={market.recent_signals} />}
      {market.recovery?.status === "ok" && <section aria-label="Bảng kiểm thị trường phục hồi" data-testid="recovery">
        <h3>Bảng kiểm &ldquo;Thị trường phục hồi&rdquo;: {recoveryHead(market.recovery)}</h3>
        <ul className="bm-list">{market.recovery.checks.map((c) => <li key={c.id}>
          <span className={`pill ${c.met === null ? "" : c.met ? "good" : "warn"}`}>{c.met === null ? "chưa có số" : c.met ? "đạt" : "chưa"}</span>{" "}
          {c.label}{c.met !== null && <span className="caption"> · {c.figure}</span>}
          {c.met === null && <span className="muted"> · {c.figure.replace(/^chưa có số /, "")}</span>}</li>)}</ul>
        <p className="caption">Đếm điều kiện trên số liệu phiên, không phải khuyến nghị mua bán. Điều kiện chưa có số không tính là đạt hay chưa.</p>
      </section>}
      {board.status === "ok" ? <>
        <h3>Thanh khoản và độ rộng</h3>
        <p>Giá trị khớp lệnh HOSE <strong>{num(board.value_matched_bn)} tỷ đồng</strong> ({num(board.volume_matched, 0)} cp)
          {hose.status === "ok" && <> · HOSE công bố tổng (gồm thỏa thuận) {num(hose.total_value_bn)} tỷ đồng</>}</p>
        {hose.status === "ok" && liquidity?.status === "ok" && <p data-testid="hose-liquidity">Giá trị HOSE công bố: {baseText(liquidity)}{" "}
          <span className="caption">({liquidity.previous_skipped ? "phiên gần nhất có số" : "phiên trước"} {num(liquidity.previous_bn)} tỷ, trung bình {liquidity.avg_sessions ?? 20}
          phiên {num(liquidity.avg20_bn)} tỷ)</span></p>}
        {hose.status === "ok" && liquidity && liquidity.status !== "ok" && <p className="muted">So với nền: chưa có số liệu ({liquidity.reason}).</p>}
        <p><span className="positive">{board.breadth.up} tăng</span> · <span className="negative">{board.breadth.down} giảm</span> ·{" "}
          {board.breadth.flat} đứng giá · {board.breadth.no_trade} không giao dịch</p>
        {board.spread && spreadText(board.spread, vnPct) && <p data-testid="spread">Lan tỏa: {spreadText(board.spread, vnPct)}
          <span className="caption"> · mọi mã HOSE có giao dịch, cùng trọng số; VN-Index tính theo vốn hóa</span></p>}
        {market.flows && <FlowRows flows={market.flows} />}
        <h3>Khối ngoại</h3>
        {board.foreign ? <>
          <p>Mua {num(board.foreign.buy_volume, 0)} cp / {num(board.foreign.buy_value_bn)} tỷ · Bán {num(board.foreign.sell_volume, 0)} cp /{" "}
            {num(board.foreign.sell_value_bn)} tỷ · Ròng <strong className={tone(board.foreign.net_value_bn)}>{signed(board.foreign.net_value_bn)} tỷ</strong></p>
          {board.foreign.top_sell.length > 0 && <p>Bán ròng mạnh: {board.foreign.top_sell.map((x) => `${x.symbol} ${signed(x.net_value_bn)} tỷ`).join("; ")}</p>}
          {board.foreign.top_buy.length > 0 && <p>Mua ròng mạnh: {board.foreign.top_buy.map((x) => `${x.symbol} ${signed(x.net_value_bn)} tỷ`).join("; ")}</p>}
        </> : <p className="muted">{foreignGap(board)}</p>}
        {hose.status === "ok" && <p className="caption">HOSE công bố: mua {num(hose.foreign.buy_value_bn)} tỷ · bán {num(hose.foreign.sell_value_bn)} tỷ ·
          ròng {signed(hose.foreign.net_value_bn)} tỷ.</p>}
      </> : <><Gap what="Giá trị giao dịch, độ rộng, khối ngoại và ngành" section={board} />
        {market.flows && <FlowRows flows={market.flows} />}</>}
      {market.proprietary.status === "ok" ? <>
        <h3>{proprietaryHead(market.proprietary)}</h3>
        <p>Mua {num(market.proprietary.buy_volume, 0)} cp / {num(market.proprietary.buy_value_bn)} tỷ · Bán {num(market.proprietary.sell_volume, 0)} cp /{" "}
          {num(market.proprietary.sell_value_bn)} tỷ · Ròng <strong className={tone(market.proprietary.net_value_bn)}>{signed(market.proprietary.net_value_bn)} tỷ</strong></p>
        {market.proprietary.top_sell && market.proprietary.top_sell.length > 0 &&
          <p>Bán ròng mạnh: {market.proprietary.top_sell.map((x) => `${x.symbol} ${signed(x.net_value_bn)} tỷ`).join("; ")}</p>}
        {market.proprietary.top_buy && market.proprietary.top_buy.length > 0 &&
          <p>Mua ròng mạnh: {market.proprietary.top_buy.map((x) => `${x.symbol} ${signed(x.net_value_bn)} tỷ`).join("; ")}</p>}
        {market.proprietary.top_reason && <p className="caption">Không có mã mua, bán ròng mạnh: {market.proprietary.top_reason}.</p>}
        <p className="caption">Nguồn: {market.proprietary.source}.</p>
      </> : <>
        <h3>Tự doanh</h3>
        <p className="muted">Chưa có số liệu ({market.proprietary.reason}).</p>
      </>}
      {board.status === "ok" && board.sectors.length > 0 && <>
        <h3>Ngành (toàn HOSE): {board.sectors.filter((s) => Number(s.pct) > 0).length}/{board.sectors.length} ngành tăng</h3>
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
      <p className="caption">Số liệu công khai (VNDirect, HOSE, RSS CafeF/Vietstock/Vneconomy); chỉ để theo dõi, không phải khuyến nghị.</p>
    </section>
  );
}
