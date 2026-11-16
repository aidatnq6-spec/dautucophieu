"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { hanoiDate } from "../lib/format";
import { CatalystTimeline } from "./catalyst-timeline";
import type { Catalyst } from "./thesis-questions";

export type Coming = Catalyst & { symbol: string; auto: boolean; due: boolean; symbols?: string[] };
const REPORT_SOURCE = "Thông tư 96/2020 Điều 14";

/** The report deadlines falling on the same day (often dozens of tickers on the 20th after a quarter) become one line naming how many. */
export function grouped(items: Coming[]): Coming[] {
  const same = new Map<string, Coming[]>();
  for (const c of items) if (c.auto && c.source === REPORT_SOURCE && c.on) same.set(`${c.on}|${c.text}`, [...(same.get(`${c.on}|${c.text}`) ?? []), c]);
  const out: Coming[] = [], done = new Set<string>();
  for (const c of items) {
    const key = `${c.on}|${c.text}`, group = c.auto && c.source === REPORT_SOURCE ? same.get(key) : undefined;
    if (!group || group.length < 2) { out.push(c); continue; }
    if (done.has(key)) continue;
    done.add(key);
    const [head, ...rest] = c.text.split(" (");
    out.push({ ...c, symbol: "", id: `report-${c.on}`, symbols: group.map((g) => g.symbol).sort(),
      text: `${head} của ${group.length} mã${rest.length ? ` (${rest.join(" (")}` : ""}` });
  }
  return out;
}
type Data = { days: number; items: Coming[] };

/** Two tickers may carry the same catalyst id; the timeline keys each by ticker and id. */
export function keyed(items: Coming[]): Coming[] {
  return items.map((c) => ({ ...c, id: `${c.symbol}:${c.id}` }));
}

export function ComingTimeline({ items, today }: { items: Coming[]; today: string }) {
  const rows = keyed(grouped(items));
  const by = Object.fromEntries(rows.map((c) => [c.id, c]));
  return <CatalystTimeline label="Mốc sắp tới của các mã theo dõi" items={rows} today={today} due={rows.filter((c) => c.due).map((c) => c.id)}
    lead={(c) => by[c.id].symbols ? <span className="pill ct-symbol">{by[c.id].symbols!.length} mã</span>
      : <Link className="pill ct-symbol" href={`/research/${by[c.id].symbol}`}>{by[c.id].symbol}</Link>}
    actions={(c) => by[c.id].symbols ? <details className="ct-symbols"><summary>Xem {by[c.id].symbols!.length} mã</summary>
      {by[c.id].symbols!.map((s, i) => <span key={s}>{i > 0 && ", "}<Link href={`/research/${s}`}>{s}</Link></span>)}</details> : null} />;
}

/** Mốc sắp tới: the owner's catalysts of every watched ticker and the automatic ones (events, report deadlines), nearest first. */
export function ComingCatalysts() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Data>("theses/catalysts").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!d) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  return (
    <section className="surface" aria-label="Mốc sắp tới">
      <h2>Mốc sắp tới ({d.days} ngày)</h2>
      <p className="caption">Mốc bạn ghi trong luận điểm của từng mã (chưa xảy ra, kể cả mốc chưa có ngày) cùng mốc tự động: sự kiện doanh nghiệp và hạn
        công bố báo cáo. Sửa hoặc đánh dấu đã xảy ra trên trang của mã.</p>
      <ComingTimeline items={d.items} today={hanoiDate()} />
    </section>
  );
}
