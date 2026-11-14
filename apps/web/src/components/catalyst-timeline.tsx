import type { Catalyst } from "./thesis-questions";

type Item = Catalyst & { auto?: boolean };
const SIGN: Record<Catalyst["sign"], [string, string]> = { "+": ["+ Thuận lợi", "good"], "-": ["− Bất lợi", "bad"], "?": ["? Chưa đánh giá", ""] };
const dmy = (iso: string) => iso.split("-").reverse().join("/");

/** Coming first (nearest first, undated last), then those that happened; each with how many days are left. */
export function timeline(items: Item[], today: string): (Item & { days: number | null })[] {
  const day = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
  return items.map((c) => ({ ...c, days: c.on ? Math.round((day(c.on) - day(today)) / 86400000) : null }))
    .sort((a, b) => Number(a.done) - Number(b.done) || (a.on ?? "9999").localeCompare(b.on ?? "9999") || a.when.localeCompare(b.when));
}

export function daysText(days: number | null, done: boolean): string {
  if (done) return "đã xảy ra";
  if (days === null) return "";
  return days > 0 ? `còn ${days} ngày` : days === 0 ? "hôm nay" : `đã qua ${-days} ngày`;
}

/** Mốc và sự kiện as a timeline: the day (and the quarter it stands for), how far away, the sign as a coloured label, the event, its source. */
export function CatalystTimeline({ items, today }: { items: Item[]; today: string }) {
  if (!items.length) return <p className="muted">Chưa có mốc.</p>;
  return (
    <ol className="ct-list">{timeline(items, today).map((c) => <li key={c.id} className={c.done ? "ct-item ct-done" : "ct-item"}>
      <div className="ct-when"><strong>{c.on ? dmy(c.on) : c.when || "chưa có mốc"}</strong>
        {c.on && c.when && !c.when.includes("/") ? <span>{c.when}</span> : c.on && c.when && c.when !== dmy(c.on) ? <span>{c.when}</span> : null}
        <span className="ct-days">{daysText(c.days, c.done)}</span></div>
      <div className="ct-body">
        <div><span className={`pill ct-sign ${SIGN[c.sign][1]}`}>{SIGN[c.sign][0]}</span>{c.auto && <span className="pill ct-auto">tự động</span>}</div>
        <p className="ct-text">{c.text}</p>
        {c.source && <p className="caption">Nguồn: {c.source}</p>}
      </div>
    </li>)}</ol>
  );
}
