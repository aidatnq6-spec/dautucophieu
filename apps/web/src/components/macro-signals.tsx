"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Level = "green" | "yellow" | "red" | "missing" | "stale";
export type Signal = {
  id: "oil" | "usd" | "fx_gap" | "fx_ceiling" | "us10y" | "foreign" | "interbank" | "pe" | "pmi"; name: string; level: Level; value: string | null; latest_date: string | null;
  yellow: string; red: string; down_yellow: string | null; down_red: string | null; since: string | null; max_age_days: number;
  spark: { date: string; value: string }[]; next: { level: "yellow" | "red"; by: string } | null;
  level_since: string | null; level_since_open: boolean; link: string;
  move: { direction: "up" | "down" | "flat"; bad: boolean | null; by: string } | null;
  bad_side?: "up" | "down"; strict?: boolean; pe?: string | null;
};
const SHARE = new Set(["oil", "usd", "fx_gap", "fx_ceiling", "pe"]);

const dm = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const num = (v: number, digits: number) => v.toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const signed = (v: number, digits: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${num(Math.abs(v), digits)}`;
// The dot is the level against the thresholds, named so it is not read as the way things moved (owner, 21/11/2026).
const LEVEL: Record<Level, string> = { green: "Bình thường", yellow: "Cảnh báo", red: "Nguy hiểm", missing: "Chưa có số", stale: "Số cũ" };
const WORD = { yellow: "cảnh báo", red: "nguy hiểm" } as const;

/** What the light measures, in words: a 30-day change, the free rate's gap, a run of sessions or a rate. */
export function signalValue(s: Signal): string {
  if (s.value === null) return "";
  const v = Number(s.value);
  if (s.id === "oil" || s.id === "usd") return `${signed(v * 100, 1)}% trong 30 ngày`;
  if (s.id === "fx_gap") return `tự do ${v >= 0 ? "cao" : "thấp"} hơn ${num(Math.abs(v) * 100, 2)}%`;
  if (s.id === "fx_ceiling") return `còn ${num(v * 100, 2)}% tới trần biên độ`;
  if (s.id === "us10y") return `${signed(v, 2)} điểm % trong 30 ngày`;
  if (s.id === "foreign") return `bán ròng ${s.value} phiên liên tiếp`;
  if (s.id === "pe") return `P/E ${num(Number(s.pe ?? 0), 2)} · cao hơn hoặc bằng ${num(v * 100, 1)}% số phiên 5 năm`;
  if (s.id === "pmi") return `PMI ${num(v, 1)}`;
  return `${num(v, 2)}%/năm`;
}

/** The light's yellow and red thresholds, in the same words as its value; oil's falling side too. */
export function signalThresholds(s: Signal): string {
  const y = Number(s.yellow), r = Number(s.red);
  if (s.id === "oil" || s.id === "usd") {
    const up = `cảnh báo ≥ +${num(y * 100, 0)}% · nguy hiểm ≥ +${num(r * 100, 0)}%`;
    return s.down_yellow && s.down_red
      ? `${up} · giảm: cảnh báo ≤ ${signed(Number(s.down_yellow) * 100, 0)}% · nguy hiểm ≤ ${signed(Number(s.down_red) * 100, 0)}%` : up;
  }
  if (s.id === "fx_gap") return `cảnh báo ≥ ${num(y * 100, 0)}% · nguy hiểm ≥ ${num(r * 100, 0)}%`;
  if (s.id === "fx_ceiling") return `cảnh báo ≤ ${num(y * 100, 0)}% · nguy hiểm ≤ ${num(r * 100, 0)}% tới trần`;
  if (s.id === "us10y") return `cảnh báo ≥ +${num(y, 1)} · nguy hiểm ≥ +${num(r, 1)} điểm %`;
  if (s.id === "pe") return `cảnh báo ≥ ${num(y * 100, 0)}% · nguy hiểm ≥ ${num(r * 100, 0)}% số phiên 5 năm`;
  if (s.id === "pmi") return `cảnh báo < ${num(y, 0)} · nguy hiểm < ${num(r, 0)}`;
  if (s.id === "foreign") return `cảnh báo ≥ ${y} phiên · nguy hiểm ≥ ${r} phiên`;
  return `cảnh báo ≥ ${num(y, 0)}%/năm · nguy hiểm ≥ ${num(r, 0)}%/năm`;
}

/** How far the next level is, in the light's own unit. */
export function signalNext(s: Signal): string | null {
  if (!s.next) return s.level === "red" ? "đang ở mức nguy hiểm" : null;
  const by = Number(s.next.by), to = WORD[s.next.level];
  if (s.id === "foreign") return `thêm ${num(by, 0)} phiên bán ròng là mức ${to}`;
  if (s.id === "interbank" || s.id === "us10y") return `còn ${num(by, 2)} điểm % nữa là mức ${to}`;
  if (s.id === "pmi") return `còn ${num(by, 1)} điểm nữa là mức ${to}`;
  return `còn ${num(by * 100, 2)} điểm % nữa là mức ${to}`;
}

/** Since when the light has held its level, worked out from the stored days. */
export function signalSince(s: Signal): string | null {
  if (!s.level_since || s.level === "missing" || s.level === "stale") return null;
  return `${LEVEL[s.level]} ${s.level_since_open ? "ít nhất từ" : "từ"} ${dm(s.level_since)}`;
}

/** Counts of each level for the line at the top of the box. */
export function signalSummary(rows: Signal[]): string {
  const count = (l: Level) => rows.filter((s) => s.level === l).length;
  const parts = [`${count("red")} nguy hiểm`, `${count("yellow")} cảnh báo`, `${count("green")} bình thường`];
  if (count("stale")) parts.push(`${count("stale")} số cũ`);
  if (count("missing")) parts.push(`${count("missing")} chưa có số`);
  return parts.join(" · ");
}

/** Which way the measure went, with its own colour: up is the bad side for all five lights. */
export function signalMove(s: Signal): { text: string; tone: "bad" | "good" | "flat" } | null {
  const m = s.move;
  if (!m || s.level === "missing") return null;
  if (s.id === "foreign") return m.bad ? { text: "▲ đang bán ròng · chiều xấu", tone: "bad" } : { text: "▼ phiên cuối mua ròng · chiều tốt", tone: "good" };
  const by = Number(m.by);
  const size = s.id === "pmi" ? `${num(by, 1)} điểm` : SHARE.has(s.id) ? `${num(by * 100, 2)} điểm %` : `${num(by, 2)} điểm %`;
  const own = s.id === "oil" || s.id === "usd" || s.id === "us10y";  // the value line already gives the 30-day change
  const span = own ? "" : s.id === "pmi" ? " so với tháng trước" : " so với 30 ngày trước";
  if (m.direction === "flat") return { text: `→ đi ngang${span}`, tone: "flat" };
  const amount = own ? "" : ` ${size}`;
  return { text: `${m.direction === "up" ? "▲ tăng" : "▼ giảm"}${amount}${span} · ${m.bad ? "chiều xấu" : "chiều tốt"}`, tone: m.bad ? "bad" : "good" };
}

/** The light's own measure over 30 days, with its yellow and red lines (both sides for oil). */
function Spark({ s }: { s: Signal }) {
  if (s.spark.length < 2) return null;
  const values = s.spark.map((p) => Number(p.value));
  const marks = [[s.yellow, "ms-mark-yellow"], [s.red, "ms-mark-red"], [s.down_yellow, "ms-mark-yellow"], [s.down_red, "ms-mark-red"]]
    .filter((m): m is [string, string] => m[0] !== null).map(([v, cls]) => ({ v: Number(v), cls }));
  const lo = Math.min(...values, ...marks.map((m) => m.v)), hi = Math.max(...values, ...marks.map((m) => m.v)), span = hi - lo || 1;
  const y = (v: number) => 28 - ((v - lo) / span) * 26;
  const line = values.map((v, i) => `${(i / (values.length - 1)) * 100},${y(v)}`).join(" ");
  return (
    <svg className="ms-spark" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">
      {marks.map((m) => <line key={`${m.cls}${m.v}`} x1="0" x2="100" y1={y(m.v)} y2={y(m.v)} className={m.cls} />)}
      <polyline points={line} />
    </svg>
  );
}

/** Đèn tín hiệu rủi ro vĩ mô: five lights on stored figures; a missing or old figure is said, never shown as green. */
export function MacroSignals() {
  const [rows, setRows] = useState<Signal[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<{ signals: Signal[] }>("macro/signals").then((d) => setRows(d.signals), (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  return (
    <section className="surface" aria-label="Đèn tín hiệu rủi ro vĩ mô">
      <h2>Đèn tín hiệu rủi ro vĩ mô</h2>
      <p className="caption">Năm đèn tính từ số đã lưu, với ngưỡng bạn đã duyệt. Telegram báo một lần khi một đèn đổi mức. Chỉ mô tả dữ liệu,
        không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!rows && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {rows && <>
        <p className="ms-summary" aria-label="Tóm tắt các đèn"><strong>{signalSummary(rows)}</strong></p>
        <ul className="ms-list" aria-label="Các đèn tín hiệu">{rows.map((s) => {
          const next = signalNext(s), since = signalSince(s), move = signalMove(s);
          return (
            <li key={s.id} data-testid={`signal-${s.id}`}>
              <span className={`ms-dot ms-${s.level}`} aria-hidden="true" />
              <div className="ms-body">
                <a href={s.link} className="ms-name"><strong>{s.name}</strong></a> <span className={`ms-level ms-${s.level}-ink`}>{LEVEL[s.level]}</span>
                {since && <span className="caption"> · {since}</span>}
                <div>
                  {s.level === "missing" ? <span className="muted">chưa có số{s.latest_date ? ` đủ 30 ngày (mới nhất ${dm(s.latest_date)})` : ""}</span>
                    : <>{signalValue(s)}{s.latest_date && <span className="caption"> · số ngày {dm(s.latest_date)}</span>}
                      {s.level === "stale" && <span className="caption"> (quá {s.max_age_days} ngày, không tô màu)</span>}</>}
                </div>
                {move && <div className={`ms-move ms-move-${move.tone}`}>{move.text}</div>}
                {next && <div className="ms-next">{next}</div>}
                <div className="caption">{signalThresholds(s)}{s.since && ` · số liệu từ ${dm(s.since)}, chưa đủ 30 ngày`}</div>
              </div>
              <Spark s={s} />
            </li>
          );
        })}</ul>
      </>}
    </section>
  );
}
