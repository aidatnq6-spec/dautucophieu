"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

export type Failing = { key: string; source: string; label: string; fails: number; since: string; error: string; alerted: boolean };
type Sources = { last_run: string | null; checked: number; failing: Failing[]; threshold: number };

const when = (iso: string) => new Date(iso).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", day: "2-digit",
  month: "2-digit", year: "numeric" });

/** The failing items gathered by source, with the longest run in a row and the earliest start. */
export function bySource(failing: Failing[]): { source: string; labels: string[]; fails: number; since: string; error: string }[] {
  const out = new Map<string, { source: string; labels: string[]; fails: number; since: string; error: string }>();
  for (const f of failing) {
    const g = out.get(f.source) ?? { source: f.source, labels: [], fails: 0, since: f.since, error: f.error };
    g.labels.push(f.label);
    g.fails = Math.max(g.fails, f.fails);
    if (f.since < g.since) g.since = f.since;
    out.set(f.source, g);
  }
  return [...out.values()];
}

/** Tình trạng nguồn số liệu: the public sources failing since the last macro run; three runs in a row are told over Telegram. */
export function SourceStatusSection() {
  const [s, setS] = useState<Sources | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Sources>("settings/sources").then(setS, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Tình trạng nguồn số liệu">
      <h2>Tình trạng nguồn số liệu</h2>
      {error ? <p className="errors" role="alert">{error}</p> : !s ? <p className="muted fx-loading" role="status">Đang tải…</p> : <>
        <p className="caption">Lượt lấy số vĩ mô gần nhất: {s.last_run ? when(s.last_run) : "chưa có"} ({s.checked} chỉ số và chuỗi). Nguồn lỗi từ {s.threshold} lượt
          liên tiếp được nhắc một lần qua Telegram, và nhắc lại khi lấy được trở lại; số đã lưu vẫn giữ.</p>
        {s.failing.length === 0 ? <p className="positive">Mọi nguồn đều lấy được ở lượt gần nhất.</p> : <ul>{bySource(s.failing).map((g) => (
          <li key={g.source}><strong>{g.source}</strong>: {g.labels.join(", ")} — lỗi {g.fails} lượt liên tiếp từ {when(g.since)}{" "}
            <span className="caption">({g.error})</span></li>))}
        </ul>}
      </>}
    </section>
  );
}
