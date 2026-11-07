"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

export type T = string | number;  // a date (weekly, daily bars) or Hà Nội wall-clock seconds (hourly bars), as the chart keys them
type Price = { date: T; price: string };
type Base = { cross: T; low_date: T; low: string; zone_from: T; zone_to: T; vs_prev: "higher" | "lower" | null };
type Channel = { kind: string; from: Price; to: Price; slope: string; top: Price; lower_now: string; upper_now: string; double_now: string };
type Status = { state: "below" | "inside" | "above"; since: T; close: string; lower: string; upper: string };
type Break = { date: T; close: string; lower: string; from: Price; to: Price };
export type Frame = "1W" | "1D" | "1H";
export type Channels = { symbol: string; label: string; unit: string | null; basis: "ohlc" | "close"; note: string | null; frame: "W" | "D" | "H"; n: number;
  reason: string | null; bases: Base[]; zero: number | null; points: Partial<Record<"0" | "1" | "2", Price>>; channels: Channel[]; status: Status | null;
  breaks: Break[]; in_progress: { t: T; c: string } | null; last_bar: T | null; bars: number };

/** Lookback for point 0 by frame: years of weeks, months of days, weeks of hours (about a year of hourly candles is kept). */
export const LOOKBACK: Record<Frame, { opts: number[]; def: number; unit: string; word: string; label: string }> = {
  "1W": { opts: [3, 5, 10], def: 5, unit: "năm", word: "tuần", label: "Tuần" },
  "1D": { opts: [6, 12, 24], def: 12, unit: "tháng", word: "ngày", label: "Ngày" },
  "1H": { opts: [2, 4, 8], def: 4, unit: "tuần", word: "1 giờ", label: "1 giờ" },
};
const FRAMES = Object.keys(LOOKBACK) as Frame[];

const pad = (n: number) => String(n).padStart(2, "0");
export function fmtT(t: T): string {
  if (typeof t === "number") {
    const d = new Date(t * 1000);
    return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)}/${d.getUTCFullYear()} ${pad(d.getUTCHours())}:00`;
  }
  return `${t.slice(8, 10)}/${t.slice(5, 7)}/${t.slice(0, 4)}`;
}
const num = (v: string) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 2 });
const fixed2 = (v: string) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fixed4 = (v: string) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 4 });

export function kindLabel(kind: string, count: number): string {
  if (count === 1) return "Kênh basic 0-2 (cũng là final)";
  if (kind === "basic") return "Kênh basic 0-2";
  if (kind === "final") return "Kênh final";
  return `Kênh tăng tốc ${kind.replace("accel", "")}`;
}

export function statusLine(s: Status, lastBar: T, word: string): string {
  const where = s.state === "below" ? `dưới cạnh dưới kênh final (${fixed2(s.lower)})`
    : s.state === "above" ? `trên cạnh trên kênh final (${fixed2(s.upper)})` : `trong kênh final (${fixed2(s.lower)} – ${fixed2(s.upper)})`;
  return `Nến ${word} ${fmtT(lastBar)} đóng cửa ${num(s.close)} — ${where} từ ${fmtT(s.since)}`;
}

export function BarChannels() {
  const [rows, setRows] = useState<{ id: string; label: string }[] | null>(null);
  const [symbol, setSymbol] = useState("VNINDEX");
  const [frame, setFrame] = useState<Frame>("1W");
  const [n, setN] = useState<Record<Frame, number>>({ "1W": LOOKBACK["1W"].def, "1D": LOOKBACK["1D"].def, "1H": LOOKBACK["1H"].def });
  const [data, setData] = useState<Channels | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<{ rows: { id: string; label: string }[] }>("trend/channels").then((d) => setRows(d.rows), () => setRows([]));
  }, []);
  useEffect(() => {
    api<Channels>(`trend/channels/${encodeURIComponent(symbol)}/${frame}/${n[frame]}`)
      .then((d) => { setData(d); setError(null); }, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol, frame, n]);
  const look = LOOKBACK[frame];
  const shown = data && data.symbol === symbol && `1${data.frame}` === frame && data.n === n[frame] ? data : null;
  const unit = shown?.unit ? ` ${shown.unit}` : "";
  return (
    <section className="surface" aria-label="Đáy nhịp và kênh tăng">
      <h2>Đáy nhịp và kênh tăng</h2>
      <div className="pb-head">
        <label className="field wc-pick"><span>Mã</span>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {(rows && rows.length ? rows : [{ id: "VNINDEX", label: "VN-Index" }]).map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
          </select></label>
        <span className="pb-toggle" role="radiogroup" aria-label="Khung nến">{FRAMES.map((f) =>
          <button key={f} type="button" role="radio" aria-checked={frame === f} className={`btn ${frame === f ? "primary" : ""}`}
            onClick={() => setFrame(f)}>{LOOKBACK[f].label}</button>)}</span>
        <span className="pb-toggle" role="group" aria-label="Điểm 0 trong">{look.opts.map((v) =>
          <button key={v} type="button" className={`btn ${n[frame] === v ? "primary" : ""}`} aria-pressed={n[frame] === v}
            onClick={() => setN((old) => ({ ...old, [frame]: v }))}>{v} {look.unit}</button>)}</span>
      </div>
      {error && <p className="errors" role="alert">{error}</p>}
      {!error && !shown && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {shown && <>
        {shown.status && shown.last_bar !== null && <p className={`wc-status ${shown.status.state}`}>{statusLine(shown.status, shown.last_bar, look.word)}.</p>}
        {shown.reason && <p className="muted">Chưa có kênh: {shown.reason}.</p>}
        {Object.keys(shown.points).length > 0 && <p className="caption wrap">
          {(["0", "1", "2"] as const).filter((k) => shown.points[k]).map((k) => `Điểm ${k}: ${num(shown.points[k]!.price)} (${fmtT(shown.points[k]!.date)})`).join(" · ")}</p>}
        {shown.channels.length > 0 && <div className="pb-scroll"><table className="pb-table">
          <caption className="caption">Các kênh (giá trị tại nến {look.word} {shown.last_bar !== null ? fmtT(shown.last_bar) : "—"}{unit})</caption>
          <thead><tr><th>Kênh</th><th>Nối từ</th><th>Đến</th><th className="num">Dốc/nến</th><th>Đỉnh giữa</th>
            <th className="num">Cạnh dưới</th><th className="num">Cạnh trên</th><th className="num">Gấp đôi</th></tr></thead>
          <tbody>{shown.channels.map((c) => <tr key={c.kind}><td>{kindLabel(c.kind, shown.channels.length)}</td>
            <td>{num(c.from.price)} ({fmtT(c.from.date)})</td><td>{num(c.to.price)} ({fmtT(c.to.date)})</td><td className="num">{fixed4(c.slope)}</td>
            <td>{num(c.top.price)} ({fmtT(c.top.date)})</td><td className="num">{fixed2(c.lower_now)}</td><td className="num">{fixed2(c.upper_now)}</td>
            <td className="num">{fixed2(c.double_now)}</td></tr>)}</tbody>
        </table></div>}
        {shown.bases.length > 0 && <div className="pb-scroll"><table className="pb-table">
          <caption className="caption">Vùng đáy MACD nến {look.word} trong {shown.n} {look.unit}</caption>
          <thead><tr><th>Vùng</th><th>Từ – đến</th><th className="num">Đáy</th><th>Nến đáy</th><th>MACD cắt lên</th><th>So đáy trước</th></tr></thead>
          <tbody>{shown.bases.map((b, i) => <tr key={String(b.cross)} className={i === shown.zero ? "pb-row-now" : undefined}>
            <td>d{i + 1}{i === shown.zero ? " · điểm 0" : ""}</td><td>{fmtT(b.zone_from)} – {fmtT(b.zone_to)}</td><td className="num">{num(b.low)}</td>
            <td>{fmtT(b.low_date)}</td><td>{fmtT(b.cross)}</td><td>{b.vs_prev === null ? "—" : b.vs_prev === "higher" ? "cao hơn" : "thấp hơn"}</td></tr>)}</tbody>
        </table></div>}
        {shown.breaks.length > 0 && <details className="mc-table">
          <summary>Các lần phá kênh final ({shown.breaks.length})</summary>
          <div className="pb-scroll"><table className="pb-table">
            <thead><tr><th>Nến</th><th className="num">Đóng cửa</th><th className="num">Cạnh dưới lúc đó</th><th>Kênh final lúc đó</th></tr></thead>
            <tbody>{shown.breaks.map((b) => <tr key={String(b.date)}><td>{fmtT(b.date)}</td><td className="num">{num(b.close)}</td><td className="num">{fixed2(b.lower)}</td>
              <td>{num(b.from.price)} ({fmtT(b.from.date)}) → {num(b.to.price)} ({fmtT(b.to.date)})</td></tr>)}</tbody>
          </table></div>
        </details>}
        <p className="caption wrap">
          Thang thường, nến {look.word}. Vùng đáy: từ lúc MACD (12/26/9) cắt xuống Signal đến lúc cắt lên; đáy là mức {shown.basis === "ohlc" ? "thấp nhất (râu nến)" : "đóng cửa thấp nhất (nguồn chỉ có giá đóng cửa)"} trong vùng;
          vùng vẽ từ 2 nến trước đáy; đáy chỉ được biết từ nến cắt lên. Điểm 0 = đáy vùng thấp nhất trong {shown.n} {look.unit}. Kênh = các cạnh của bao lồi dưới
          nối các vùng đáy từ điểm 0, đo theo số nến (khoảng nghỉ cuối tuần, ban đêm không làm cong đường); mỗi vùng nối ở điểm thoải nhất nhìn từ điểm nối trước;
          cạnh trên song song qua đỉnh cao nhất giữa hai điểm nối, gấp đôi = hai lần độ rộng. Giá trị chỉ tính tới nến đã kết thúc gần nhất, không kéo kênh ra
          tương lai. Phá kênh = nến đầu tiên đóng cửa dưới kênh final đang có hiệu lực lúc đó (chỉ dùng các đáy đã xác nhận tới nến đó).
          {shown.in_progress && ` Nến ${fmtT(shown.in_progress.t)} chưa kết thúc (giá ${num(shown.in_progress.c)}) nên chưa tính.`}
          {shown.note && ` ${shown.note}`} Chỉ là đường kẻ theo luật, không phải tín hiệu mua bán.
        </p>
      </>}
    </section>
  );
}
