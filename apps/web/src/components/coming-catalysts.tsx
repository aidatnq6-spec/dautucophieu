"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { hanoiDate } from "../lib/format";
import { CatalystTimeline } from "./catalyst-timeline";
import type { Catalyst } from "./thesis-questions";

export type Coming = Catalyst & { symbol: string; auto: boolean; due: boolean };
type Data = { days: number; items: Coming[] };

/** Two tickers may carry the same catalyst id; the timeline keys each by ticker and id. */
export function keyed(items: Coming[]): Coming[] {
  return items.map((c) => ({ ...c, id: `${c.symbol}:${c.id}` }));
}

export function ComingTimeline({ items, today }: { items: Coming[]; today: string }) {
  const rows = keyed(items);
  const symbol = Object.fromEntries(rows.map((c) => [c.id, c.symbol]));
  return <CatalystTimeline label="Mốc sắp tới của các mã theo dõi" items={rows} today={today} due={rows.filter((c) => c.due).map((c) => c.id)}
    lead={(c) => <Link className="pill ct-symbol" href={`/research/${symbol[c.id]}`}>{symbol[c.id]}</Link>} />;
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
