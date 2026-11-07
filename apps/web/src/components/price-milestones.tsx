"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Row = { kind: "current" | "trough" | "low_now" | "pb_floor"; label: string; date: string; price: string; drop: string; pb: string | null; pe: string | null;
  vs_floor: string | null; deeper: number };
export type Milestones = { symbol: string; reason: string | null; threshold: string; date: string; close: string; peak: { date: string; price: string };
  drawdown: string; trend: "up" | "down" | null; corrections: { peak: string; trough: string; depth: string }[];
  floor: { pb: string; date: string; price: string; from: string } | null; rows: Row[]; weeks: number; from: string; since: string | null; omitted_troughs: number };

const THRESHOLDS = [10, 15, 20] as const;
const vnd = (v: string) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 0 });
const x2 = (v: string | null) => (v === null ? "—" : Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const pct = (v: string) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${Math.abs(Number(v) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
const month = (d: string) => `${d.slice(5, 7)}/${d.slice(0, 4)}`;
const day = (d: string) => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;

export function headline(m: Milestones): string {
  const where = Number(m.drawdown) < 0 ? `${pct(m.drawdown)} từ đỉnh` : "đang ở đỉnh";
  return `${m.symbol} · giá ${vnd(m.close)}, ${where} ${vnd(m.peak.price)} (${month(m.peak.date)})`;
}

export function coverageNote(m: Milestones): string {
  const span = m.since === null
    ? "Chưa có chuỗi P/B: liệt kê trên toàn bộ lịch sử giá."
    : `Liệt kê từ ${month(m.since)} (tuần đầu có P/B)${m.omitted_troughs > 0
      ? `; ${m.omitted_troughs} đáy cũ hơn thấp hơn giá hôm nay không liệt kê vì P/B, P/E theo số liệu hôm nay không còn ý nghĩa.` : "."}`;
  return `${span} ${m.corrections.length} đợt chỉnh đã hoàn tất trong khoảng này.`;
}

export function PriceMilestones({ symbol }: { symbol: string }) {
  const [threshold, setThreshold] = useState<(typeof THRESHOLDS)[number]>(15);
  const [data, setData] = useState<Milestones | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<Milestones>(`fairvalue/milestones/${encodeURIComponent(symbol)}/${threshold}`)
      .then((d) => { setData(d); setError(null); }, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol, threshold]);
  const shown = data && data.threshold === (threshold / 100).toFixed(4) ? data : null;
  return (
    <section className="pb-section" aria-label={`Mốc giá quá khứ ${symbol}`}>
      <div className="pb-head">
        <strong>{shown && !shown.reason ? `Mốc giá quá khứ — ${headline(shown)}` : `Mốc giá quá khứ ${symbol}`}</strong>
        <span className="pb-toggle" role="group" aria-label="Ngưỡng tách nhịp">{THRESHOLDS.map((t) =>
          <button key={t} type="button" className={`btn ${threshold === t ? "primary" : ""}`} aria-pressed={threshold === t} onClick={() => setThreshold(t)}>{t}%</button>)}</span>
      </div>
      {error && <p className="errors" role="alert">{error}</p>}
      {!error && !shown && <p className="muted fx-loading" role="status">Đang tải mốc giá…</p>}
      {shown?.reason && <p className="muted">Chưa có mốc giá: {shown.reason}.</p>}
      {shown && !shown.reason && <>
        <div className="pb-scroll">
          <table className="pb-table">
            <caption className="caption">Các mốc giá có thật trong lịch sử của mã, cao xuống thấp</caption>
            <thead><tr><th>Mốc</th><th>Ngày</th><th className="num">Giá</th><th className="num">Giảm từ đỉnh</th><th className="num">Đợt chỉnh trước sâu hơn</th>
              <th className="num">P/B</th><th className="num">P/E</th><th className="num">So giá tại P/B thấp nhất</th></tr></thead>
            <tbody>{shown.rows.map((r) => <tr key={`${r.kind}-${r.date}`} className={r.kind === "current" ? "pb-row-now" : undefined}>
              <td>{r.label}</td><td>{day(r.date)}</td><td className="num">{vnd(r.price)}</td><td className="num">{pct(r.drop)}</td>
              <td className="num">{r.deeper}/{shown.corrections.length}</td><td className="num">{x2(r.pb)}</td><td className="num">{x2(r.pe)}</td>
              <td className="num">{r.vs_floor === null ? "—" : pct(r.vs_floor)}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="caption wrap">
          Nhịp tách theo giá đóng cửa tuần đã điều chỉnh: một đỉnh hoặc đáy chỉ được xác nhận khi giá đã đi ngược {threshold}% từ đó; đáy của nhịp đang
          giảm chưa được xác nhận. Đỉnh = đỉnh xác nhận gần nhất khi đang giảm, hoặc mức cao nhất của nhịp đang tăng.
          {" "}{coverageNote(shown)} P/B, P/E tại mỗi mốc tính theo vốn chủ và lợi nhuận của tuần mới nhất, không phải bội số lúc đó.
          {shown.floor && ` Giá tại P/B thấp nhất = P/B ${x2(shown.floor.pb)} (tuần ${day(shown.floor.date)}) × vốn chủ/cổ phiếu hôm nay.`}
          {" "}Chỉ là mốc đã xảy ra: không dự phóng bao lâu nữa giá về, không tính xác suất, chỉ để đối chiếu.
        </p>
      </>}
    </section>
  );
}
