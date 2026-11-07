"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Price = { date: string; price: string };
type Base = { cross: string; low_date: string; low: string; zone_from: string; zone_to: string; vs_prev: "higher" | "lower" | null };
type Channel = { kind: string; from: Price; to: Price; slope: string; top: Price; lower_now: string; upper_now: string; double_now: string };
type Status = { state: "below" | "inside" | "above"; since: string; close: string; lower: string; upper: string };
type Break = { date: string; close: string; lower: string; from: Price; to: Price };
export type Channels = { symbol: string; label: string; unit: string | null; basis: "ohlc" | "close"; note: string | null; years: number; reason: string | null;
  bases: Base[]; zero: number | null; points: Partial<Record<"0" | "1" | "2", Price>>; channels: Channel[]; status: Status | null; breaks: Break[];
  in_progress: { t: string; c: string } | null; last_week: string | null; weeks: number };

const YEARS = [3, 5, 10] as const;
const day = (d: string) => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;
const num = (v: string) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 2 });
const fixed2 = (v: string) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function kindLabel(kind: string, count: number): string {
  if (count === 1) return "Kênh basic 0-2 (cũng là final)";
  if (kind === "basic") return "Kênh basic 0-2";
  if (kind === "final") return "Kênh final";
  return `Kênh tăng tốc ${kind.replace("accel", "")}`;
}

export function statusLine(s: Status, lastWeek: string): string {
  const where = s.state === "below" ? `dưới cạnh dưới kênh final (${fixed2(s.lower)})`
    : s.state === "above" ? `trên cạnh trên kênh final (${fixed2(s.upper)})` : `trong kênh final (${fixed2(s.lower)} – ${fixed2(s.upper)})`;
  return `Tuần ${day(lastWeek)} đóng cửa ${num(s.close)} — ${where} từ tuần ${day(s.since)}`;
}

export function WeeklyChannels() {
  const [rows, setRows] = useState<{ id: string; label: string }[] | null>(null);
  const [symbol, setSymbol] = useState("VNINDEX");
  const [years, setYears] = useState<(typeof YEARS)[number]>(5);
  const [data, setData] = useState<Channels | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<{ rows: { id: string; label: string }[] }>("trend/channels").then((d) => setRows(d.rows), () => setRows([]));
  }, []);
  useEffect(() => {
    api<Channels>(`trend/channels/${encodeURIComponent(symbol)}/${years}`)
      .then((d) => { setData(d); setError(null); }, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol, years]);
  const shown = data && data.symbol === symbol && data.years === years ? data : null;
  const unit = shown?.unit ? ` ${shown.unit}` : "";
  return (
    <section className="surface" aria-label="Đáy nhịp tuần và kênh tăng">
      <h2>Đáy nhịp tuần và kênh tăng</h2>
      <div className="pb-head">
        <label className="field wc-pick"><span>Mã</span>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {(rows && rows.length ? rows : [{ id: "VNINDEX", label: "VN-Index" }]).map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
          </select></label>
        <span className="pb-toggle" role="group" aria-label="Điểm 0 trong">{YEARS.map((y) =>
          <button key={y} type="button" className={`btn ${years === y ? "primary" : ""}`} aria-pressed={years === y} onClick={() => setYears(y)}>{y} năm</button>)}</span>
      </div>
      {error && <p className="errors" role="alert">{error}</p>}
      {!error && !shown && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {shown && <>
        {shown.status && shown.last_week && <p className={`wc-status ${shown.status.state}`}>{statusLine(shown.status, shown.last_week)}.</p>}
        {shown.reason && <p className="muted">Chưa có kênh: {shown.reason}.</p>}
        {Object.keys(shown.points).length > 0 && <p className="caption wrap">
          {(["0", "1", "2"] as const).filter((k) => shown.points[k]).map((k) => `Điểm ${k}: ${num(shown.points[k]!.price)} (${day(shown.points[k]!.date)})`).join(" · ")}</p>}
        {shown.channels.length > 0 && <div className="pb-scroll"><table className="pb-table">
          <caption className="caption">Các kênh (giá trị tại tuần {shown.last_week ? day(shown.last_week) : "—"}{unit})</caption>
          <thead><tr><th>Kênh</th><th>Nối từ</th><th>Đến</th><th className="num">Dốc/tuần</th><th>Đỉnh giữa</th>
            <th className="num">Cạnh dưới</th><th className="num">Cạnh trên</th><th className="num">Gấp đôi</th></tr></thead>
          <tbody>{shown.channels.map((c) => <tr key={c.kind}><td>{kindLabel(c.kind, shown.channels.length)}</td>
            <td>{num(c.from.price)} ({day(c.from.date)})</td><td>{num(c.to.price)} ({day(c.to.date)})</td><td className="num">{fixed2(c.slope)}</td>
            <td>{num(c.top.price)} ({day(c.top.date)})</td><td className="num">{fixed2(c.lower_now)}</td><td className="num">{fixed2(c.upper_now)}</td>
            <td className="num">{fixed2(c.double_now)}</td></tr>)}</tbody>
        </table></div>}
        {shown.bases.length > 0 && <div className="pb-scroll"><table className="pb-table">
          <caption className="caption">Vùng đáy MACD tuần trong {shown.years} năm</caption>
          <thead><tr><th>Vùng</th><th>Từ – đến</th><th className="num">Đáy</th><th>Tuần đáy</th><th>MACD cắt lên</th><th>So đáy trước</th></tr></thead>
          <tbody>{shown.bases.map((b, i) => <tr key={b.cross} className={i === shown.zero ? "pb-row-now" : undefined}>
            <td>d{i + 1}{i === shown.zero ? " · điểm 0" : ""}</td><td>{day(b.zone_from)} – {day(b.zone_to)}</td><td className="num">{num(b.low)}</td>
            <td>{day(b.low_date)}</td><td>{day(b.cross)}</td><td>{b.vs_prev === null ? "—" : b.vs_prev === "higher" ? "cao hơn" : "thấp hơn"}</td></tr>)}</tbody>
        </table></div>}
        {shown.breaks.length > 0 && <details className="mc-table">
          <summary>Các lần phá kênh final ({shown.breaks.length})</summary>
          <div className="pb-scroll"><table className="pb-table">
            <thead><tr><th>Tuần</th><th className="num">Đóng cửa</th><th className="num">Cạnh dưới lúc đó</th><th>Kênh final lúc đó</th></tr></thead>
            <tbody>{shown.breaks.map((b) => <tr key={b.date}><td>{day(b.date)}</td><td className="num">{num(b.close)}</td><td className="num">{fixed2(b.lower)}</td>
              <td>{num(b.from.price)} ({day(b.from.date)}) → {num(b.to.price)} ({day(b.to.date)})</td></tr>)}</tbody>
          </table></div>
        </details>}
        <p className="caption wrap">
          Thang thường. Vùng đáy: từ lúc MACD tuần (12/26/9) cắt xuống Signal đến lúc cắt lên; đáy là mức {shown.basis === "ohlc" ? "thấp nhất (râu nến)" : "đóng cửa thấp nhất (nguồn chỉ có giá đóng cửa)"} trong vùng;
          vùng vẽ từ 2 tuần trước đáy; đáy chỉ được biết từ tuần cắt lên. Điểm 0 = đáy vùng thấp nhất trong {shown.years} năm. Kênh = các cạnh của bao lồi dưới
          nối các vùng đáy từ điểm 0 (mỗi vùng nối ở điểm thoải nhất nhìn từ điểm nối trước); cạnh trên song song qua đỉnh cao nhất giữa hai điểm nối,
          gấp đôi = hai lần độ rộng. Giá trị chỉ tính tới tuần đã kết thúc gần nhất, không kéo kênh ra tương lai. Phá kênh = tuần đầu tiên đóng cửa dưới
          kênh final đang có hiệu lực lúc đó (chỉ dùng các đáy đã xác nhận tới tuần đó).
          {shown.in_progress && ` Tuần ${day(shown.in_progress.t)} chưa kết thúc (giá ${num(shown.in_progress.c)}) nên chưa tính.`}
          {shown.note && ` ${shown.note}`} Chỉ là đường kẻ theo luật, không phải tín hiệu mua bán.
        </p>
      </>}
    </section>
  );
}
