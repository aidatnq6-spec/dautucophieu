"use client";
import Link from "next/link";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

export type Glance = {
  session_date: string | null;
  kpis: { market_value: string; unrealized_gain: string; day_change: string | null; day_change_ratio: string | null; vnindex: string | null;
    vnindex_change_ratio: string | null; performance: { portfolio: string; vnindex: string; since: string } | null; room: string | null; over_budget: string | null;
    held_count: number; unpriced: string[]; no_prior_close: string[]; price_dates: string[] };
  attention: { items?: { level: "high" | "low"; kind: string; symbol: string | null; text: string; href: string }[]; events: { symbol: string; kind: string; title: string; key_date: string }[]; over_limit: { name: string; kind: string; weight: string }[];
    journal_reviews: { entry_id: string; symbol: string; kind: string; change: string }[]; latest_report: { report_id: string; session_date: string } | null };
};

export const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** What the quick numbers cover: the session, the price day, how many holdings, the unit. */
export function scopeLine(g: Glance): string {
  const k = g.kpis;
  const prices = k.price_dates.length === 1 ? `giá ngày ${day(k.price_dates[0])}` : k.price_dates.length ? `giá các ngày ${k.price_dates.map(day).join(", ")}` : null;
  return [g.session_date ? `Phiên ${day(g.session_date)}` : "Chưa có phiên VN-Index đã lưu", prices,
    k.held_count ? `${k.held_count} mã đang giữ` : "chưa nắm giữ mã nào", "đơn vị đồng"].filter(Boolean).join(" · ");
}

/** One line under each quick number: how it is made, or which holdings it leaves out, or why it is empty. */
export function kpiNotes(g: Glance) {
  const k = g.kpis;
  const left = (symbols: string[], why: string) => `Chưa tính ${symbols.join(", ")}: ${why}`;
  const unpriced = k.unpriced.length ? left(k.unpriced, "chưa có giá") : null;
  const session = k.day_change === null ? (k.held_count ? "Chưa có hai phiên đóng cửa đã lưu cho mã đang giữ" : "Chưa nắm giữ mã nào")
    : k.no_prior_close.length ? left(k.no_prior_close, "thiếu giá đóng cửa phiên trước") : "So với giá đóng cửa phiên trước";
  return { value: unpriced ?? "Số lượng × giá gần nhất", gain: unpriced ?? "Giá trị theo giá gần nhất − giá vốn", day: session,
    vnindex: k.vnindex === null ? "Chưa có chuỗi VN-Index đã lưu" : "Điểm đóng cửa phiên gần nhất",
    performance: "Lợi suất theo thời gian, không tính tiền nạp/rút", budget: "Vốn cho cổ phiếu − giá vốn đang nắm" };
}

function Signed({ value, ratio }: { value?: string | null; ratio?: string | null }) {
  const raw = value ?? ratio;
  if (raw === null || raw === undefined) return <span className="muted">—</span>;
  const negative = raw.startsWith("-"), zero = !/[1-9]/.test(raw);
  const text = value != null ? formatVnd(value.replace(/^-/, "")) : formatRatio(raw.replace(/^-/, ""), 1);
  return <span className={zero ? "" : negative ? "negative" : "positive"}>{zero ? "" : negative ? "−" : "+"}{text}</span>;
}

/** Quick numbers for the last session; each one comes from a page that shows it in full. */
export function QuickNumbers({ g }: { g: Glance }) {
  const k = g.kpis, n = kpiNotes(g);
  const note = (text: string) => <span className="kpi-note">{text}</span>;
  return (
    <section className="surface" aria-label="Số liệu nhanh">
      <p className="caption kpi-scope">{scopeLine(g)}</p>
      <div className="kpi-row">
      <div><span className="kpi-label">Giá trị danh mục</span><strong data-testid="kpi-value">{formatVnd(k.market_value)}</strong>{note(n.value)}</div>
      <div><span className="kpi-label">Phiên gần nhất</span><strong><Signed value={k.day_change} /></strong>
        <span className="caption"><Signed ratio={k.day_change_ratio} /></span>{note(n.day)}</div>
      <div><span className="kpi-label">Lãi/lỗ chưa thực hiện</span><strong><Signed value={k.unrealized_gain} /></strong>{note(n.gain)}</div>
      <div><span className="kpi-label">VN-Index</span><strong>{k.vnindex ? formatDecimal(k.vnindex, 2) : "—"}</strong>
        <span className="caption"><Signed ratio={k.vnindex_change_ratio} /></span>{note(n.vnindex)}</div>
      {k.performance && <div><span className="kpi-label">Từ {day(k.performance.since)}</span>
        <strong><Signed ratio={k.performance.portfolio} /></strong>
        <span className="caption">VN-Index <Signed ratio={k.performance.vnindex} /> · <Link href="/portfolio">chi tiết</Link></span>{note(n.performance)}</div>}
      {(k.room !== null || k.over_budget !== null) && <div><span className="kpi-label">Vốn cho cổ phiếu</span>
        <strong>{k.over_budget ? <span className="negative">Đã vượt {formatVnd(k.over_budget)}</span> : <>Còn trống {formatVnd(k.room)}</>}</strong>{note(n.budget)}</div>}
      </div>
    </section>
  );
}

const KIND: Record<string, string> = { dividend_cash: "Cổ tức tiền", issue: "Phát hành", meeting: "Đại hội cổ đông" };
const JOURNAL_KIND: Record<string, string> = { buy: "mua", sell: "bán", hold: "đang giữ" };

/** One list of what deserves a look today, gathered from Lịch sự kiện, Phân bổ and Nhật ký; nothing here is a recommendation. */
export function WorthALook({ g }: { g: Glance }) {
  const a = g.attention;
  const items = a.items ?? [];
  const empty = !items.length && !a.events.length && !a.over_limit.length && !a.journal_reviews.length;
  return (
    <section className="surface" aria-label="Cần để ý">
      <h2>Cần để ý</h2>
      {empty ? <p className="muted">Không có gì cần để ý hôm nay.</p> : <ul className="watch-list">
        {items.filter((i) => i.level === "high").map((i) => <li key={i.text}>{i.kind === "system" ? <span className="pill warn">Hệ thống</span> : <span className="pill bad">Cần quyết định</span>} <Link href={i.href}>{i.text.replace(/^Hệ thống · /, "")}</Link></li>)}
        {a.events.map((e) => <li key={`${e.symbol}-${e.key_date}-${e.kind}`}>
          <span className="pill">Sự kiện</span> <strong>{e.symbol}</strong> {KIND[e.kind] ?? e.kind} ngày {day(e.key_date)}: {e.title} · <Link href="/events">Lịch sự kiện</Link></li>)}
        {a.over_limit.map((o) => <li key={o.name}>
          <span className="pill bad">Vượt ngưỡng</span> {o.kind === "sector" ? "Ngành " : ""}<strong>{o.name}</strong> chiếm {formatRatio(o.weight, 1)} · <Link href="/portfolio">Phân bổ</Link></li>)}
        {a.journal_reviews.map((j) => <li key={j.entry_id}>
          <span className="pill warn">Nhật ký</span> <strong>{j.symbol}</strong> (lúc {JOURNAL_KIND[j.kind] ?? j.kind}) đã đi <Signed ratio={j.change} /> so với lúc ghi · <Link href="/journal">xem lại lý do</Link></li>)}
        {items.filter((i) => i.level === "low").map((i) => <li key={i.text}><span className="pill">Mới</span> <Link href={i.href}>{i.text}</Link></li>)}
      </ul>}
      {a.latest_report && <p className="caption">Bản tin mới nhất: <Link href={`/reports/${a.latest_report.report_id}`}>phiên {day(a.latest_report.session_date)}</Link></p>}
    </section>
  );
}
