"use client";
import { type RefObject, useEffect, useRef, useState } from "react";
import type { IChartApi, ISeriesApi, SeriesType, Time } from "lightweight-charts";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

type Row = { symbol: string; kind: "index" | "macro" | "stock"; price: string | null; ref: string | null; change: string | null; change_pct: string | null;
  ceiling?: string | null; floor?: string | null; high?: string | null; low?: string | null; volume?: number | null; time: string | null;
  label?: string; basis?: "close" | "24h"; unit?: string; reason?: string | null };
type Board = { as_of: string; stocks_as_of?: string; session_open: boolean; rows: Row[]; missing: string[]; errors: string[] };
type Bar = { t: string | number; o?: string; h?: string; l?: string; c: string; v?: number };
type Chart = { symbol: string; interval: "1D" | "1H"; bars: Bar[]; macd: { t: string | number; macd: number; signal: number; hist: number }[];
  rsi: { t: string | number; v: number }[]; fetched_at: string | null; stale: boolean; reason: string | null; unit?: string;
  style?: "line"; as_of?: string | null };
const GROUPS: [Row["kind"], string][] = [["index", "Chỉ số"], ["macro", "Vĩ mô"], ["stock", "Cổ phiếu"]];
const day = (iso: string) => iso.slice(0, 10).split("-").reverse().slice(0, 2).join("/");

/** Which candle the row's latest price belongs to, keyed like the chart's bars: a date for daily bars (the trading date for stocks,
 * Hà Nội date for indices, UTC date for Coinbase's daily candles), Hà Nội wall-clock seconds at the hour's start for hourly bars.
 * Rows read from a daily close have no live price. */
function liveKey(row: Row, board: Board, interval: "1D" | "1H"): string | number | null {
  if (row.price === null || (row.kind === "macro" && row.basis !== "24h")) return null;
  const at = Date.parse(row.kind === "stock" ? board.stocks_as_of ?? board.as_of : row.time ?? board.as_of);
  if (Number.isNaN(at)) return null;
  const wall = Math.floor(at / 1000) + 7 * HOUR;
  if (interval === "1H") return wall - (wall % HOUR);
  if (row.kind === "stock") return row.time;
  return new Date((row.kind === "macro" ? Math.floor(at / 1000) : wall) * 1000).toISOString().slice(0, 10);
}

// Every 20 s at any hour: Bitcoin and gold trade around the clock; the server keeps stocks for 5 min outside the session.
const POLL = 20_000;
const RELOAD_GAP = 120_000;
const HOUR = 3600;
const C = { up: "#137556", down: "#b14249", ink: "#183247", line: "#dce4eb", muted: "#576777", macd: "#245edb", signal: "#d97706", rsi: "#7c3aed" };

/** Exchange colours: ceiling purple, floor cyan, reference yellow, then up green and down red. */
function tone(r: Row): string {
  if (r.price === null || r.ref === null) return "";
  const p = Number(r.price);
  if (r.ceiling != null && p >= Number(r.ceiling)) return "tb-ceil";
  if (r.floor != null && p <= Number(r.floor)) return "tb-floor";
  return p > Number(r.ref) ? "tb-up" : p < Number(r.ref) ? "tb-down" : "tb-ref";
}
const signed = (v: string) => (v.startsWith("-") || Number(v) === 0 ? formatDecimal(v, 2) : `+${formatDecimal(v, 2)}`);
const pct = (v: string) => (v.startsWith("-") || Number(v) === 0 ? formatRatio(v, 2) : `+${formatRatio(v, 2)}`);

function PriceList({ board, selected, onSelect }: { board: Board; selected: string; onSelect: (s: string) => void }) {
  return (
    <table className="tb-list" aria-label="Bảng giá">
      <thead><tr><th>Mã</th><th className="num">Giá</th><th className="num">+/−</th><th className="num">%</th></tr></thead>
      {GROUPS.map(([kind, title]) => {
        const rows = board.rows.filter((r) => r.kind === kind);
        return rows.length > 0 && <tbody key={kind}>
          <tr className="tb-group"><th colSpan={4} scope="colgroup">{title}</th></tr>
          {rows.map((r) => {
            const t = tone(r);
            const when = r.kind === "macro" && r.time ? (r.basis === "24h" ? "so với 24 giờ trước" : `đóng cửa ${day(r.time)}`) : null;
            return (
              <tr key={r.symbol} className={r.symbol === selected ? "tb-selected" : undefined} aria-selected={r.symbol === selected}
                tabIndex={0} onClick={() => onSelect(r.symbol)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(r.symbol); } }}>
                <th scope="row" className={t}>{r.label ?? r.symbol}{when && <span className="tb-when">{when}</span>}</th>
                <td className={`num ${t}`}>{r.price === null
                  ? <span title={r.reason ?? "Chưa khớp lệnh trong phiên"}>—</span> : formatDecimal(r.price, 2)}</td>
                <td className={`num ${t}`}>{r.change === null ? "—" : signed(r.change)}</td>
                <td className={`num ${t}`}>{r.change_pct === null ? "—" : pct(r.change_pct)}</td>
              </tr>
            );
          })}
        </tbody>;
      })}
    </table>
  );
}

type ChartRefs = { box: RefObject<HTMLDivElement | null>; price: RefObject<ISeriesApi<SeriesType> | null>; last: RefObject<Bar | null>;
  latest: RefObject<{ t: string | number | null; p: number | null }> };

/** The open candle follows the board's price; a new candle waits for the source, so no open, high or low is made up.
 * Called when the price changes and again once the (asynchronously built) chart exists. */
function applyLive({ box, price, last, latest }: ChartRefs, style: Chart["style"]) {
  const series = price.current;
  const bar = last.current;
  const { t: at, p } = latest.current;
  if (!series || !bar || at === null || p === null || at !== bar.t) return;
  const time = bar.t as Time;
  if (style === "line") {
    series.update({ time, value: p });
  } else {
    const high = Math.max(Number(bar.h), p);
    const low = Math.min(Number(bar.l), p);
    series.update({ time, open: Number(bar.o), high, low, close: p });
    last.current = { ...bar, h: String(high), l: String(low), c: String(p) };
  }
  if (box.current) box.current.dataset.liveClose = String(p);
}

function CandleChart({ data, liveT, livePrice }: { data: Chart; liveT: string | number | null; livePrice: number | null }) {
  const box = useRef<HTMLDivElement>(null);
  const price = useRef<ISeriesApi<SeriesType> | null>(null);
  const last = useRef<Bar | null>(null);
  const latest = useRef<{ t: string | number | null; p: number | null }>({ t: null, p: null });
  useEffect(() => {
    let chart: IChartApi | null = null;
    let cancelled = false;
    void import("lightweight-charts").then(({ createChart, CandlestickSeries, HistogramSeries, LineSeries }) => {
      if (cancelled || !box.current) return;
      chart = createChart(box.current, {
        autoSize: true, layout: { background: { color: "#fff" }, textColor: C.ink, panes: { separatorColor: C.line } },
        grid: { vertLines: { color: "#f0f3f6" }, horzLines: { color: "#f0f3f6" } }, localization: { locale: "vi-VN" },
        timeScale: { timeVisible: data.interval === "1H", secondsVisible: false, borderColor: C.line }, rightPriceScale: { borderColor: C.line },
      });
      const t = (v: string | number) => v as Time;
      if (data.style === "line") {  // closes only (Vĩ mô feeds): a line, no candles or volume
        const line = chart.addSeries(LineSeries, { color: C.macd, lineWidth: 2 });
        line.setData(data.bars.map((b) => ({ time: t(b.t), value: Number(b.c) })));
        price.current = line;
      } else {
        const candles = chart.addSeries(CandlestickSeries, { upColor: C.up, downColor: C.down, borderVisible: false, wickUpColor: C.up, wickDownColor: C.down });
        candles.setData(data.bars.map((b) => ({ time: t(b.t), open: Number(b.o), high: Number(b.h), low: Number(b.l), close: Number(b.c) })));
        price.current = candles;
        const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "vol", lastValueVisible: false, priceLineVisible: false });
        chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
        volume.setData(data.bars.map((b) => ({ time: t(b.t), value: b.v ?? 0, color: Number(b.c) >= Number(b.o) ? "rgba(19,117,86,.35)" : "rgba(177,66,73,.35)" })));
      }
      const hist = chart.addSeries(HistogramSeries, { lastValueVisible: false, priceLineVisible: false }, 1);
      hist.setData(data.macd.map((m) => ({ time: t(m.t), value: m.hist, color: m.hist >= 0 ? "rgba(19,117,86,.5)" : "rgba(177,66,73,.5)" })));
      chart.addSeries(LineSeries, { color: C.macd, lineWidth: 1, priceLineVisible: false }, 1).setData(data.macd.map((m) => ({ time: t(m.t), value: m.macd })));
      chart.addSeries(LineSeries, { color: C.signal, lineWidth: 1, priceLineVisible: false }, 1).setData(data.macd.map((m) => ({ time: t(m.t), value: m.signal })));
      const rsi = chart.addSeries(LineSeries, { color: C.rsi, lineWidth: 1, priceLineVisible: false }, 2);
      rsi.setData(data.rsi.map((r) => ({ time: t(r.t), value: r.v })));
      for (const level of [70, 30]) rsi.createPriceLine({ price: level, color: C.muted, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "" });
      const panes = chart.panes();
      panes[1]?.setHeight(110);
      panes[2]?.setHeight(90);
      last.current = data.bars.at(-1) ?? null;
      applyLive({ box, price, last, latest }, data.style);
      const shown = data.interval === "1D" ? 180 : 120;
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, data.bars.length - shown), to: data.bars.length + 3 });
    });
    return () => { cancelled = true; price.current = null; last.current = null; chart?.remove(); };
  }, [data]);
  useEffect(() => {
    latest.current = { t: liveT, p: livePrice };
    applyLive({ box, price, last, latest }, data.style);
  });
  return <div ref={box} className="tb-canvas" data-testid="tb-canvas" />;
}

/** Bảng giá và biểu đồ: indices and watched tickers during the session, and candles with MACD and RSI for the one picked. */
export function TrendBoard() {
  const [board, setBoard] = useState<Board | null>(null);
  const [selected, setSelected] = useState("VNINDEX");
  const [interval, setInterval_] = useState<"1D" | "1H">("1D");
  const [chart, setChart] = useState<Chart | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const reloadedAt = useRef(0);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let alive = true;
    const load = () => {
      if (document.hidden) { timer = setTimeout(load, POLL); return; }
      api<Board>("trend/board").then((b) => { if (!alive) return; setBoard(b); setMessage(null); timer = setTimeout(load, POLL); },
        (e) => { if (!alive) return; setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải bảng giá."); timer = setTimeout(load, POLL); });
    };
    load();
    return () => { alive = false; clearTimeout(timer); };
  }, []);

  useEffect(() => {
    let alive = true;
    api<Chart>(`trend/chart/${encodeURIComponent(selected)}/${interval}`).then((c) => { if (alive) setChart(c); },
      () => { if (alive) setChart({ symbol: selected, interval, bars: [], macd: [], rsi: [], fetched_at: null, stale: false, reason: "Lỗi tải biểu đồ" }); });
    return () => { alive = false; };
  }, [selected, interval, reload]);

  const row = board?.rows.find((r) => r.symbol === selected);
  const current = chart && chart.symbol === selected && chart.interval === interval ? chart : null;
  const liveT = row && board ? liveKey(row, board, interval) : null;
  const livePrice = liveT !== null && row?.price ? Number(row.price) : null;
  const lastT = current?.bars.at(-1)?.t;
  const behind = liveT !== null && livePrice !== null && lastT !== undefined && liveT > lastT;  // a newer candle has started: read the source again
  useEffect(() => {
    if (!behind) return;
    const wait = Math.max(0, reloadedAt.current + RELOAD_GAP - Date.now());
    const timer = setTimeout(() => { reloadedAt.current = Date.now(); setReload((n) => n + 1); }, wait);
    return () => clearTimeout(timer);
  }, [behind, current]);  // each read that still lacks the new candle waits RELOAD_GAP before the next
  return (
    <section className="surface" aria-label="Bảng giá và biểu đồ">
      <h2>Bảng giá và biểu đồ</h2>
      <div className="tb-layout">
        <div className="tb-chart" role="group" aria-label={`Biểu đồ ${selected}`}>
          <div className="tb-head">
            <strong>{row?.label ?? selected}</strong>
            {row?.price && <span className={tone(row)}>{formatDecimal(row.price, 2)} {row.change && signed(row.change)} {row.change_pct && `(${pct(row.change_pct)})`}</span>}
            <span className="tb-intervals" role="radiogroup" aria-label="Khung nến">
              {(["1D", "1H"] as const).map((iv) => <button key={iv} type="button" role="radio" aria-checked={interval === iv}
                className={`btn ${interval === iv ? "primary" : ""}`} onClick={() => setInterval_(iv)}>{iv === "1D" ? "Ngày" : "1 giờ"}</button>)}
            </span>
          </div>
          {!current && <p className="muted fx-loading" role="status">Đang tải biểu đồ…</p>}
          {current?.reason && <p className="muted">{current.reason}.</p>}
          {current && !current.reason && <>
            <CandleChart data={current} liveT={liveT} livePrice={livePrice} />
            <p className="caption" data-testid="tb-chart-caption">{current.style === "line"
              ? `Giá đóng cửa ${current.interval === "1D" ? "theo ngày" : "theo giờ"} · ${current.bars.length} điểm · ${current.unit ?? ""} · số mới nhất ${current.as_of ?? "—"}`
              : `${current.interval === "1D" ? "Nến ngày" : "Nến 1 giờ"} · ${current.bars.length} nến · ${current.unit ?? ""}`}
              {" "}· dưới: MACD (12, 26, 9) và RSI (14), đường 70/30
              {current.style === "line" ? " · dữ liệu phần mềm đã lưu cho bảng Xu hướng"
                : ` · Vnstock, đọc ${current.fetched_at ? new Date(current.fetched_at).toLocaleString("vi-VN") : "—"}`}
              {current.stale ? " — nguồn đang lỗi, đây là bản đã lưu" : ""}. Biểu đồ dùng thư viện mã nguồn mở Lightweight Charts của TradingView.</p>
          </>}
        </div>
        <div className="tb-side">
          {message && <p className="errors" role="alert">{message}</p>}
          {!board && !message && <p className="muted fx-loading" role="status">Đang tải bảng giá…</p>}
          {board && <>
            <PriceList board={board} selected={selected} onSelect={setSelected} />
            <p className="caption" data-testid="tb-status">{board.session_open
              ? `Trong phiên · cập nhật ${new Date(board.as_of).toLocaleTimeString("vi-VN")}, tự làm mới mỗi 20 giây`
              : `Ngoài giờ giao dịch · cổ phiếu và chỉ số là giá phiên gần nhất, đọc lúc ${new Date(board.stocks_as_of ?? board.as_of).toLocaleString("vi-VN")}; Bitcoin và vàng vẫn cập nhật mỗi 20 giây`}.
              Nến đang mở trên biểu đồ chạy theo giá này; MACD, RSI và nến mới cập nhật khi đọc lại nguồn.
              Cổ phiếu tính bằng nghìn đồng, chỉ số bằng điểm; tím là giá trần, xanh lơ là giá sàn, vàng là tham chiếu.
              Vĩ mô: Bitcoin và vàng (PAXG, token bám giá vàng) theo Coinbase, so với 24 giờ trước; DXY, US10Y, VN10Y, dầu WTI là giá đóng cửa gần
              nhất so với phiên trước, vì nguồn miễn phí chỉ có giá ngày; lợi suất tính bằng %, thay đổi bằng điểm phần trăm.
              {board.missing.length > 0 && ` Chưa có giá: ${board.missing.join(", ")}.`}</p>
            {board.errors.map((e) => <p key={e} className="errors">{e}.</p>)}
            {row?.kind === "stock" && row.volume !== null && <p className="caption">KL {selected}: {formatVnd(String(row.volume), { unit: false })} ·
              cao {formatDecimal(row.high, 2)} · thấp {formatDecimal(row.low, 2)} · trần {formatDecimal(row.ceiling, 2)} · sàn {formatDecimal(row.floor, 2)}</p>}
          </>}
        </div>
      </div>
    </section>
  );
}
