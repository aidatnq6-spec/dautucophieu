"use client";
import { type RefObject, useEffect, useMemo, useRef, useState } from "react";
import type { IChartApi, IPriceLine, ISeriesApi, ISeriesMarkersPluginApi, SeriesType, Time } from "lightweight-charts";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";
import { type Marker, type Segment, channelMarkers, channelSegments } from "./channel-overlay";
import { alpha, resolveColor, useTheme } from "../lib/theme";
import { type Add, type At, type Drawing, DrawingList, DrawingToolbar, type Interval, type Tool, dragResult, useChartDrawings } from "./chart-drawings";
import { PriceAlerts } from "./price-alerts";
import { type Channels, type Frame, LOOKBACK, fmtT } from "./bar-channels";

type Row = { symbol: string; kind: "index" | "macro" | "stock"; price: string | null; ref: string | null; change: string | null; change_pct: string | null;
  ceiling?: string | null; floor?: string | null; high?: string | null; low?: string | null; volume?: number | null; time: string | null;
  label?: string; basis?: "close" | "24h"; unit?: string; reason?: string | null };
type Board = { as_of: string; stocks_as_of?: string; session_open: boolean; rows: Row[]; missing: string[]; errors: string[] };
type Bar = { t: string | number; o?: string; h?: string; l?: string; c: string; v?: number };
type Chart = { symbol: string; interval: Interval; bars: Bar[]; macd: { t: string | number; macd: number; signal: number; hist: number }[];
  rsi: { t: string | number; v: number }[]; fetched_at: string | null; stale: boolean; reason: string | null; unit?: string;
  style?: "line"; as_of?: string | null };
const GROUPS: [Row["kind"], string][] = [["index", "Chỉ số"], ["macro", "Vĩ mô"], ["stock", "Cổ phiếu"]];
const day = (iso: string) => iso.slice(0, 10).split("-").reverse().slice(0, 2).join("/");

/** The bar a day falls in: the week's Monday for weekly bars, the month's first day for monthly ones, as the server groups them. */
export function periodStart(day: string, interval: Interval): string {
  if (interval === "1M") return `${day.slice(0, 7)}-01`;
  if (interval !== "1W") return day;
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}

/** Which candle the row's latest price belongs to, keyed like the chart's bars: a date for daily bars (the trading date for stocks,
 * Hà Nội date for indices, UTC date for Coinbase's daily candles) and the week's or month's start for longer ones, Hà Nội
 * wall-clock seconds at the hour's start for hourly bars. Rows read from a daily close have no live price. */
function liveKey(row: Row, board: Board, interval: Interval): string | number | null {
  if (row.price === null || (row.kind === "macro" && row.basis !== "24h")) return null;
  const at = Date.parse(row.kind === "stock" ? board.stocks_as_of ?? board.as_of : row.time ?? board.as_of);
  if (Number.isNaN(at)) return null;
  const wall = Math.floor(at / 1000) + 7 * HOUR;
  if (interval === "1H") return wall - (wall % HOUR);
  const day = row.kind === "stock" ? row.time : new Date((row.kind === "macro" ? Math.floor(at / 1000) : wall) * 1000).toISOString().slice(0, 10);
  return day === null ? null : periodStart(day, interval);
}

const FRAMES: [Interval, string, string][] = [["1H", "1 giờ", "giờ"], ["1D", "Ngày", "ngày"], ["1W", "Tuần", "tuần"], ["1M", "Tháng", "tháng"]];
const SHOWN: Record<Interval, number> = { "1H": 120, "1D": 180, "1W": 104, "1M": 120 };

// Every 20 s at any hour: Bitcoin and gold trade around the clock; the server keeps stocks for 5 min outside the session.
const POLL = 20_000;
const RELOAD_GAP = 120_000;
const HOUR = 3600;
/** The chart library draws on canvas and takes only real colours, read from the current theme whenever a chart is built. */
const palette = () => {
  const v = (name: string) => resolveColor(`var(--${name})`);
  return { up: v("good"), down: v("bad"), ink: v("ink"), line: v("line"), muted: v("muted"), macd: v("brand"), signal: v("signal"), rsi: v("rsi"), draw: v("draw"), bg: v("paper"), grid: v("chart-grid") };
};

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

type Overlay = { segments: Segment[]; markers: Marker[] };
type ChartProps = { data: Chart; liveT: string | number | null; livePrice: number | null; drawings: Drawing[]; tool: Tool;
  onDrawn: (add: Add) => void; overlay: Overlay | null };

function CandleChart({ data, liveT, livePrice, drawings, tool, onDrawn, overlay }: ChartProps) {
  const box = useRef<HTMLDivElement>(null);
  const theme = useTheme();
  const chartRef = useRef<IChartApi | null>(null);
  const LineRef = useRef<typeof import("lightweight-charts").LineSeries | null>(null);
  const MarkersRef = useRef<typeof import("lightweight-charts").createSeriesMarkers | null>(null);
  const [built, setBuilt] = useState(0);
  const toolRef = useRef(tool);
  const drawnRef = useRef(onDrawn);
  useEffect(() => { toolRef.current = tool; drawnRef.current = onDrawn; });
  const price = useRef<ISeriesApi<SeriesType> | null>(null);
  const last = useRef<Bar | null>(null);
  const latest = useRef<{ t: string | number | null; p: number | null }>({ t: null, p: null });
  useEffect(() => {
    let chart: IChartApi | null = null;
    let cancelled = false;
    let unlisten = () => {};
    void import("lightweight-charts").then(({ createChart, CandlestickSeries, HistogramSeries, LineSeries, createSeriesMarkers }) => {
      if (cancelled || !box.current) return;
      const C = palette();
      chart = createChart(box.current, {
        autoSize: true, layout: { background: { color: C.bg }, textColor: C.ink, panes: { separatorColor: C.line } },
        grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } }, localization: { locale: "vi-VN" },
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
        volume.setData(data.bars.map((b) => ({ time: t(b.t), value: b.v ?? 0, color: alpha(Number(b.c) >= Number(b.o) ? C.up : C.down, 0.35) })));
      }
      const hist = chart.addSeries(HistogramSeries, { lastValueVisible: false, priceLineVisible: false }, 1);
      hist.setData(data.macd.map((m) => ({ time: t(m.t), value: m.hist, color: alpha(m.hist >= 0 ? C.up : C.down, 0.5) })));
      chart.addSeries(LineSeries, { color: C.macd, lineWidth: 1, priceLineVisible: false }, 1).setData(data.macd.map((m) => ({ time: t(m.t), value: m.macd })));
      chart.addSeries(LineSeries, { color: C.signal, lineWidth: 1, priceLineVisible: false }, 1).setData(data.macd.map((m) => ({ time: t(m.t), value: m.signal })));
      const rsi = chart.addSeries(LineSeries, { color: C.rsi, lineWidth: 1, priceLineVisible: false }, 2);
      rsi.setData(data.rsi.map((r) => ({ time: t(r.t), value: r.v })));
      for (const level of [70, 30]) rsi.createPriceLine({ price: level, color: C.muted, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "" });
      // Shares, not pixels: the chart is still unsized here (autoSize), so pixel heights came out as a sliver for MACD.
      // 320/110/90 of the 520 px box, kept in proportion on the 420 px phone layout.
      chart.panes().forEach((pane, i) => pane.setStretchFactor([320, 110, 90][i] ?? 1));
      last.current = data.bars.at(-1) ?? null;
      applyLive({ box, price, last, latest }, data.style);
      const shown = SHOWN[data.interval];
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, data.bars.length - shown), to: data.bars.length + 3 });
      // Drawing: press on the price pane, drag, let go. A dashed draft follows the pointer; the points snap to the nearest candle.
      // Read from the page's own pointer events, with the chart's scrolling off while a tool is held (see the effect below).
      const el = box.current;
      const c = chart;
      const pointAt = (e: PointerEvent): At | null => {
        const at = el.getBoundingClientRect();
        const x = e.clientX - at.left, y = e.clientY - at.top;
        const bar = data.bars[Math.round(c.timeScale().coordinateToLogical(x) ?? -1)];
        const p = price.current?.coordinateToPrice(y);
        return bar && p != null && x <= c.timeScale().width() && y >= 0 && y <= (c.panes()[0]?.getHeight() ?? 0) ? { t: bar.t, p } : null;
      };
      let from: At | null = null, to: At | null = null;
      let draft: ISeriesApi<"Line"> | null = null, draftLevel: IPriceLine | null = null;
      const show = (at: At) => {
        to = at;
        if (toolRef.current === "hline") {
          draftLevel ??= price.current?.createPriceLine({ price: at.p, color: C.draw, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "" }) ?? null;
          draftLevel?.applyOptions({ price: at.p });
        } else if (from) {
          draft ??= c.addSeries(LineSeries, { color: C.draw, lineWidth: 2, lineStyle: 2, lastValueVisible: false, priceLineVisible: false,
            crosshairMarkerVisible: false, autoscaleInfoProvider: () => null });
          const ends = from.t === at.t ? [at] : [from, at].sort((a, b) => (a.t < b.t ? -1 : 1));
          draft.setData(ends.map((pt) => ({ time: pt.t as Time, value: pt.p })));
        }
      };
      const stop = () => {
        from = to = null;
        if (draft) { c.removeSeries(draft); draft = null; }
        if (draftLevel) { price.current?.removePriceLine(draftLevel); draftLevel = null; }
      };
      const onDown = (e: PointerEvent) => {
        const at = toolRef.current === "pointer" || e.button !== 0 ? null : pointAt(e);
        if (!at) return;
        e.preventDefault();
        el.setPointerCapture?.(e.pointerId);
        from = at;
        show(at);
      };
      const onMove = (e: PointerEvent) => { const at = from && pointAt(e); if (at) show(at); };
      const onUp = (e: PointerEvent) => {
        if (!from) return;
        const start = from, end = pointAt(e) ?? to ?? from;
        stop();
        const add = dragResult(toolRef.current, start, end);
        if (add) drawnRef.current(add);
      };
      const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") stop(); };
      el.addEventListener("pointerdown", onDown);
      el.addEventListener("pointermove", onMove);
      el.addEventListener("pointerup", onUp);
      el.addEventListener("pointercancel", stop);
      window.addEventListener("keydown", onKey);
      unlisten = () => {
        el.removeEventListener("pointerdown", onDown); el.removeEventListener("pointermove", onMove); el.removeEventListener("pointerup", onUp);
        el.removeEventListener("pointercancel", stop); window.removeEventListener("keydown", onKey);
      };
      chartRef.current = chart;
      LineRef.current = LineSeries;
      MarkersRef.current = createSeriesMarkers;
      setBuilt((n) => n + 1);
    });
    return () => { cancelled = true; unlisten(); price.current = null; last.current = null; chartRef.current = null; chart?.remove(); };
  }, [data, theme]);
  useEffect(() => {
    const chart = chartRef.current, series = price.current, Line = LineRef.current;
    if (!chart || !series || !Line) return;
    const C = palette();
    const lines: IPriceLine[] = [];
    const trends: ISeriesApi<"Line">[] = [];
    for (const d of drawings) {
      if (d.kind === "hline" && d.price) {
        lines.push(series.createPriceLine({ price: Number(d.price), color: C.draw, lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: "" }));
      } else if (d.kind === "trend" && d.points) {
        const trend = chart.addSeries(Line, { color: C.draw, lineWidth: 2, lastValueVisible: false, priceLineVisible: false,
          crosshairMarkerVisible: false, autoscaleInfoProvider: () => null });
        trend.setData([...d.points].sort((a, b) => (a.t < b.t ? -1 : 1)).map((pt) => ({ time: pt.t as Time, value: Number(pt.p) })));
        trends.push(trend);
      }
    }
    if (box.current) box.current.dataset.drawings = String(drawings.length);
    return () => {
      if (chartRef.current !== chart) return;  // the chart was rebuilt: its lines went with it
      for (const l of lines) series.removePriceLine(l);
      for (const t of trends) chart.removeSeries(t);
    };
  }, [drawings, built]);
  // Kênh: read-only lines and markers from the weekly channel rules, kept apart from the owner's own drawings.
  useEffect(() => {
    const chart = chartRef.current, series = price.current, Line = LineRef.current, makeMarkers = MarkersRef.current;
    if (!chart || !series || !Line || !makeMarkers || !overlay) {
      if (box.current) box.current.dataset.overlay = "0";
      return;
    }
    const added: ISeriesApi<"Line">[] = [];
    for (const seg of overlay.segments) {
      const line = chart.addSeries(Line, { color: resolveColor(seg.color), lineWidth: seg.width, lineStyle: seg.style, lastValueVisible: false, priceLineVisible: false,
        crosshairMarkerVisible: false, autoscaleInfoProvider: () => null });
      line.setData(seg.points.map((pt) => ({ time: pt.t as Time, value: pt.p })));
      added.push(line);
    }
    const markers: ISeriesMarkersPluginApi<Time> = makeMarkers(series, overlay.markers.map((m) => ({ ...m, color: resolveColor(m.color), time: m.time as Time })));
    if (box.current) box.current.dataset.overlay = String(overlay.segments.length);
    return () => {
      if (chartRef.current !== chart) return;
      markers.detach();
      for (const l of added) chart.removeSeries(l);
    };
  }, [overlay, built]);
  // While a drawing tool is held, a drag draws instead of scrolling or zooming the chart.
  useEffect(() => { chartRef.current?.applyOptions({ handleScroll: tool === "pointer", handleScale: tool === "pointer" }); }, [tool, built]);
  useEffect(() => {
    latest.current = { t: liveT, p: livePrice };
    applyLive({ box, price, last, latest }, data.style);
  });
  return <div ref={box} className={`tb-canvas${tool !== "pointer" ? " tb-drawing" : ""}`} data-testid="tb-canvas" />;
}

/** Bảng giá và biểu đồ: indices and watched tickers during the session, and candles with MACD and RSI for the one picked. */
export function TrendBoard() {
  const [board, setBoard] = useState<Board | null>(null);
  const [selected, setSelected] = useState("VNINDEX");
  const [interval, setInterval_] = useState<Interval>("1D");
  const [chart, setChart] = useState<Chart | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const reloadedAt = useRef(0);
  const tools = useChartDrawings(selected, interval);
  const [channelN, setChannelN] = useState<Record<Frame, number>>({ "1W": 0, "1D": 0, "1H": 0 });  // 0 = off, the default
  const [channels, setChannels] = useState<Channels | null>(null);
  const frameWord = FRAMES.find(([iv]) => iv === interval)?.[2] ?? "";

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

  useEffect(() => {
    let alive = true;
    const n = interval in LOOKBACK ? channelN[interval as Frame] : 0;
    if (n === 0) return;
    api<Channels>(`trend/channels/${encodeURIComponent(selected)}/${interval}/${n}`).then((c) => { if (alive) setChannels(c); },
      () => { if (alive) setChannels(null); });
    return () => { alive = false; };
  }, [selected, interval, channelN]);
  const frame = interval in LOOKBACK ? (interval as Frame) : null;
  const channelOn = frame !== null ? channelN[frame] : 0;
  const channelData = frame && channelOn > 0 && channels?.symbol === selected && `1${channels.frame}` === frame && channels.n === channelOn ? channels : null;
  const overlay = useMemo(() => (channelData && !channelData.reason ? { segments: channelSegments(channelData), markers: channelMarkers(channelData) } : null),
    [channelData]);

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
              {FRAMES.map(([iv, label]) => <button key={iv} type="button" role="radio" aria-checked={interval === iv}
                className={`btn ${interval === iv ? "primary" : ""}`} onClick={() => setInterval_(iv)}>{label}</button>)}
            </span>
          </div>
          {!current && <p className="muted fx-loading" role="status">Đang tải biểu đồ…</p>}
          {current?.reason && <p className="muted">{current.reason}.</p>}
          {current && !current.reason && <>
            <DrawingToolbar tools={tools} symbol={row?.label ?? selected} />
            {frame && <div className="tb-channels" role="group" aria-label="Kênh">
              <span className="caption">Kênh {LOOKBACK[frame].word}</span>
              {[0, ...LOOKBACK[frame].opts].map((v) => <button key={v} type="button" className={`btn ${channelOn === v ? "primary" : ""}`} aria-pressed={channelOn === v}
                onClick={() => setChannelN((old) => ({ ...old, [frame]: v }))}>{v === 0 ? "Tắt" : `${v} ${LOOKBACK[frame].unit}`}</button>)}
              {channelOn > 0 && !channelData && <span className="caption fx-loading" role="status">Đang tải kênh…</span>}
              {channelData?.reason && <span className="caption">Chưa có kênh: {channelData.reason}.</span>}
              {overlay && <span className="caption" data-testid="tb-channel-caption">Xanh: kênh basic, tăng tốc (nét đứt), final (đậm), cạnh trên và gấp đôi
                (chấm) tới nến {fmtT(channelData!.last_bar!)}; nâu: vùng đáy MACD, d1… từ điểm 0 trong {channelOn} {LOOKBACK[frame].unit};
                mũi tên đỏ: nến phá kênh final. Luật xem ở khối Đáy nhịp và kênh tăng bên dưới; không kéo ra tương lai.</span>}
            </div>}
            <CandleChart data={current} liveT={liveT} livePrice={livePrice} drawings={tools.shown} tool={tools.tool} onDrawn={tools.onDrawn}
              overlay={frame ? overlay : null} />
            <p className="caption" data-testid="tb-chart-caption">{current.style === "line"
              ? `Giá đóng cửa theo ${frameWord} · ${current.bars.length} điểm · ${current.unit ?? ""} · số mới nhất ${current.as_of ?? "—"}`
              : `${current.interval === "1H" ? "Nến 1 giờ" : `Nến ${frameWord}`} · ${current.bars.length} nến · ${current.unit ?? ""}`}
              {current.interval === "1W" || current.interval === "1M" ? ` · gộp từ nến ngày (mở đầu kỳ, cao nhất, thấp nhất, đóng cuối kỳ), ${frameWord} cuối đang chạy` : ""}
              {" "}· dưới: MACD (12, 26, 9) và RSI (14), đường 70/30
              {current.style === "line" ? " · dữ liệu phần mềm đã lưu cho bảng Xu hướng"
                : ` · Vnstock, đọc ${current.fetched_at ? new Date(current.fetched_at).toLocaleString("vi-VN") : "—"}`}
              {current.stale ? " — nguồn đang lỗi, đây là bản đã lưu" : ""}. Biểu đồ dùng thư viện mã nguồn mở Lightweight Charts của TradingView.
              Hình vẽ (màu cam) là ghi chú của bạn: đường ngang hiện ở mọi khung, đường xu hướng chỉ ở khung đã vẽ.</p>
            <DrawingList tools={tools} />
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
          <PriceAlerts symbol={selected} canAlert={row?.kind !== "macro"} />
        </div>
      </div>
    </section>
  );
}
