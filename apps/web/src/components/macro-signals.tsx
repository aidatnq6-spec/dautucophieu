"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Level = "green" | "yellow" | "red" | "missing" | "stale";
export type Signal = {
  id: "oil" | "usd" | "fx_gap" | "foreign" | "interbank"; name: string; level: Level; value: string | null; latest_date: string | null;
  yellow: string; red: string; since: string | null; max_age_days: number; spark: { date: string; value: string }[];
};

const dm = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const num = (v: number, digits: number) => v.toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const LEVEL: Record<Level, string> = { green: "Xanh", yellow: "Vàng", red: "Đỏ", missing: "Chưa có số", stale: "Số cũ" };

/** What the light measures, in words: a 30-day change, the free rate's gap, a run of sessions or a rate. */
export function signalValue(s: Signal): string {
  if (s.value === null) return "";
  const v = Number(s.value);
  if (s.id === "oil" || s.id === "usd") return `${v > 0 ? "+" : v < 0 ? "−" : ""}${num(Math.abs(v) * 100, 1)}% trong 30 ngày`;
  if (s.id === "fx_gap") return `tự do ${v >= 0 ? "cao" : "thấp"} hơn ${num(Math.abs(v) * 100, 2)}%`;
  if (s.id === "foreign") return `bán ròng ${s.value} phiên liên tiếp`;
  return `${num(v, 2)}%/năm`;
}

/** The light's yellow and red thresholds, in the same words as its value. */
export function signalThresholds(s: Signal): string {
  const y = Number(s.yellow), r = Number(s.red);
  if (s.id === "oil" || s.id === "usd") return `vàng ≥ +${num(y * 100, 0)}% · đỏ ≥ +${num(r * 100, 0)}%`;
  if (s.id === "fx_gap") return `vàng ≥ ${num(y * 100, 0)}% · đỏ ≥ ${num(r * 100, 0)}%`;
  if (s.id === "foreign") return `vàng ≥ ${y} phiên · đỏ ≥ ${r} phiên`;
  return `vàng ≥ ${num(y, 0)}%/năm · đỏ ≥ ${num(r, 0)}%/năm`;
}

function Spark({ points }: { points: Signal["spark"] }) {
  if (points.length < 2) return null;
  const values = points.map((p) => Number(p.value));
  const lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
  const d = values.map((v, i) => `${(i / (values.length - 1)) * 100},${28 - ((v - lo) / span) * 24}`).join(" ");
  return <svg className="ms-spark" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true"><polyline points={d} /></svg>;
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
      {rows && <ul className="ms-list" aria-label="Các đèn tín hiệu">{rows.map((s) => (
        <li key={s.id} data-testid={`signal-${s.id}`}>
          <span className={`ms-dot ms-${s.level}`} aria-hidden="true" />
          <div className="ms-body">
            <strong>{s.name}</strong> <span className={`ms-level ms-${s.level}-ink`}>{LEVEL[s.level]}</span>
            <div>
              {s.level === "missing" ? <span className="muted">chưa có số{s.latest_date ? ` đủ 30 ngày (mới nhất ${dm(s.latest_date)})` : ""}</span>
                : <>{signalValue(s)}{s.latest_date && <span className="caption"> · số ngày {dm(s.latest_date)}</span>}
                  {s.level === "stale" && <span className="caption"> (quá {s.max_age_days} ngày, không tô màu)</span>}</>}
            </div>
            <div className="caption">{signalThresholds(s)}{s.since && ` · số liệu từ ${dm(s.since)}, chưa đủ 30 ngày`}</div>
          </div>
          <Spark points={s.spark} />
        </li>))}</ul>}
    </section>
  );
}
