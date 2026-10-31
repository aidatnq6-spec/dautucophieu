"use client";
import { useEffect, useRef, useState } from "react";
import type { IChartApi, Time } from "lightweight-charts";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

type Row = { symbol: string; kind: "index" | "stock"; price: string | null; ref: string | null; change: string | null; change_pct: string | null;
  ceiling: string | null; floor: string | null; high: string | null; low: string | null; volume: number | null; time: string | null };
type Board = { as_of: string; session_open: boolean; rows: Row[]; missing: string[]; errors: string[] };
type Bar = { t: string | number; o: string; h: string; l: string; c: string; v: number };
type Chart = { symbol: string; interval: "1D" | "1H"; bars: Bar[]; macd: { t: string | number; macd: number; signal: number; hist: number }[];
  rsi: { t: string | number; v: number }[]; fetched_at: string | null; stale: boolean; reason: string | null; unit?: string };

const POLL = { open: 20_000, closed: 300_000 };
const C = { up: "#137556", down: "#b14249", ink: "#183247", line: "#dce4eb", muted: "#576777", macd: "#245edb", signal: "#d97706", rsi: "#7c3aed" };

/** Exchange colours: ceiling purple, floor cyan, reference yellow, then up green and down red. */
function tone(r: Row): string {
  if (r.price === null || r.ref === null) return "";
  const p = Number(r.price);
  if (r.ceiling !== null && p >= Number(r.ceiling)) return "tb-ceil";
  if (r.floor !== null && p <= Number(r.floor)) return "tb-floor";
  return p > Number(r.ref) ? "tb-up" : p < Number(r.ref) ? "tb-down" : "tb-ref";
}
const signed = (v: string) => (v.startsWith("-") || Number(v) === 0 ? formatDecimal(v, 2) : `+${formatDecimal(v, 2)}`);
const pct = (v: string) => (v.startsWith("-") || Number(v) === 0 ? formatRatio(v, 2) : `+${formatRatio(v, 2)}`);

function PriceList({ board, selected, onSelect }: { board: Board; selected: string; onSelect: (s: string) => void }) {
  return (
    <table className="tb-list" aria-label="Bảng giá">
      <thead><tr><th>Mã</th><th className="num">Giá</th><th className="num">+/−</th><th className="num">%</th></tr></thead>
      <tbody>{board.rows.map((r) => {
        const t = tone(r);
        return (
          <tr key={r.symbol} className={r.symbol === selected ? "tb-selected" : undefined} aria-selected={r.symbol === selected}
            tabIndex={0} onClick={() => onSelect(r.symbol)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(r.symbol); } }}>
            <th scope="row" className={t}>{r.symbol}</th>
            <td className={`num ${t}`}>{r.price === null ? <span title="Chưa khớp lệnh trong phiên">—</span> : formatDecimal(r.price, 2)}</td>
            <td className={`num ${t}`}>{r.change === null ? "—" : signed(r.change)}</td>
            <td className={`num ${t}`}>{r.change_pct === null ? "—" : pct(r.change_pct)}</td>
          </tr>
        );
      })}</tbody>
    </table>
  );
}

function CandleChart({ data }: { data: Chart }) {
  const box = useRef<HTMLDivElement>(null);
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
      const candles = chart.addSeries(CandlestickSeries, { upColor: C.up, downColor: C.down, borderVisible: false, wickUpColor: C.up, wickDownColor: C.down });
      candles.setData(data.bars.map((b) => ({ time: t(b.t), open: Number(b.o), high: Number(b.h), low: Number(b.l), close: Number(b.c) })));
      const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "vol", lastValueVisible: false, priceLineVisible: false });
      chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      volume.setData(data.bars.map((b) => ({ time: t(b.t), value: b.v, color: Number(b.c) >= Number(b.o) ? "rgba(19,117,86,.35)" : "rgba(177,66,73,.35)" })));
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
      const shown = data.interval === "1D" ? 180 : 120;
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, data.bars.length - shown), to: data.bars.length + 3 });
    });
    return () => { cancelled = true; chart?.remove(); };
  }, [data]);
  return <div ref={box} className="tb-canvas" data-testid="tb-canvas" />;
}

/** Bảng giá và biểu đồ: indices and watched tickers during the session, and candles with MACD and RSI for the one picked. */
export function TrendBoard() {
  const [board, setBoard] = useState<Board | null>(null);
  const [selected, setSelected] = useState("VNINDEX");
  const [interval, setInterval_] = useState<"1D" | "1H">("1D");
  const [chart, setChart] = useState<Chart | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let alive = true;
    const load = () => {
      if (document.hidden) { timer = setTimeout(load, POLL.open); return; }
      api<Board>("trend/board").then((b) => { if (!alive) return; setBoard(b); setMessage(null); timer = setTimeout(load, b.session_open ? POLL.open : POLL.closed); },
        (e) => { if (!alive) return; setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải bảng giá."); timer = setTimeout(load, POLL.closed); });
    };
    load();
    return () => { alive = false; clearTimeout(timer); };
  }, []);

  useEffect(() => {
    let alive = true;
    api<Chart>(`trend/chart/${encodeURIComponent(selected)}/${interval}`).then((c) => { if (alive) setChart(c); },
      () => { if (alive) setChart({ symbol: selected, interval, bars: [], macd: [], rsi: [], fetched_at: null, stale: false, reason: "Lỗi tải biểu đồ" }); });
    return () => { alive = false; };
  }, [selected, interval]);

  const row = board?.rows.find((r) => r.symbol === selected);
  const current = chart && chart.symbol === selected && chart.interval === interval ? chart : null;
  return (
    <section className="surface" aria-label="Bảng giá và biểu đồ">
      <h2>Bảng giá và biểu đồ</h2>
      <div className="tb-layout">
        <div className="tb-chart" role="group" aria-label={`Biểu đồ ${selected}`}>
          <div className="tb-head">
            <strong>{selected}</strong>
            {row?.price && <span className={tone(row)}>{formatDecimal(row.price, 2)} {row.change && signed(row.change)} {row.change_pct && `(${pct(row.change_pct)})`}</span>}
            <span className="tb-intervals" role="radiogroup" aria-label="Khung nến">
              {(["1D", "1H"] as const).map((iv) => <button key={iv} type="button" role="radio" aria-checked={interval === iv}
                className={`btn ${interval === iv ? "primary" : ""}`} onClick={() => setInterval_(iv)}>{iv === "1D" ? "Ngày" : "1 giờ"}</button>)}
            </span>
          </div>
          {!current && <p className="muted fx-loading" role="status">Đang tải biểu đồ…</p>}
          {current?.reason && <p className="muted">{current.reason}.</p>}
          {current && !current.reason && <>
            <CandleChart data={current} />
            <p className="caption" data-testid="tb-chart-caption">{current.interval === "1D" ? "Nến ngày" : "Nến 1 giờ"} · {current.bars.length} nến ·
              {" "}{current.unit ?? ""} · dưới: MACD (12, 26, 9) và RSI (14), đường 70/30 · Vnstock, đọc {current.fetched_at ? new Date(current.fetched_at).toLocaleString("vi-VN") : "—"}
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
              : `Ngoài giờ giao dịch · giá phiên gần nhất, đọc lúc ${new Date(board.as_of).toLocaleString("vi-VN")}`}.
              Cổ phiếu tính bằng nghìn đồng, chỉ số bằng điểm; tím là giá trần, xanh lơ là giá sàn, vàng là tham chiếu.
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
