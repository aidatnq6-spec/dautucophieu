"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Minus, MousePointer2, Spline, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal } from "../lib/format";

export type Interval = "1D" | "1H" | "1W" | "1M";
export type Point = { t: string | number; p: string };
export type Drawing = { id: string; symbol: string; kind: "hline" | "trend"; interval: Interval | null; price: string | null;
  points: [Point, Point] | null; created_at: string };
export type Tool = "pointer" | "hline" | "trend";
type View = { version: number; drawings: Drawing[] };
export type Add = { kind: "hline"; price: string } | { kind: "trend"; points: [Point, Point] };
export type At = { t: string | number; p: number };

/** A level shows on every frame; a trend line only on the frame it was drawn on (each frame keys its bars differently). */
export function drawingsFor(drawings: Drawing[], symbol: string, interval: Interval): Drawing[] {
  return drawings.filter((d) => d.symbol === symbol && (d.kind === "hline" || d.interval === interval));
}

/** The cursor's price, two decimals, as a plain decimal for the API; null when it is not a positive price. */
export function roundPrice(p: number): string | null {
  if (!Number.isFinite(p)) return null;
  const rounded = Math.round(p * 100) / 100;
  return rounded > 0 ? String(rounded) : null;
}

/** One press on the price pane, from where it went down to where it was let go: a level at the release, a trend line between two
 * different candles. Anything else draws nothing. */
export function dragResult(tool: Tool, from: At, to: At): Add | null {
  const p = roundPrice(to.p);
  if (tool === "pointer" || p === null) return null;
  if (tool === "hline") return { kind: "hline", price: p };
  const start = roundPrice(from.p);
  return start === null || from.t === to.t ? null : { kind: "trend", points: [{ t: from.t, p: start }, { t: to.t, p }] };
}

const TOOLS: [Tool, string, typeof Minus][] = [["pointer", "Con trỏ", MousePointer2], ["hline", "Đường ngang", Minus], ["trend", "Đường xu hướng", Spline]];

/** Hình vẽ: the owner's levels and trend lines for the ticker and frame shown, kept in the personal store. */
export function useChartDrawings(symbol: string, interval: Interval) {
  const [view, setView] = useState<View | null>(null);
  const [tool, setTool] = useState<Tool>("pointer");
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("trend/drawings").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải hình vẽ.")); }, []);

  const change = useCallback(async (body: Record<string, unknown>) => {
    if (!view) return;
    try {
      setView(await api<View>("trend/drawings", { method: "PUT", body: { ...body, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu hình vẽ.");
    }
  }, [view]);
  // Back to the pointer once a shape is drawn, so the chart scrolls again.
  const onDrawn = useCallback((add: Add) => {
    setTool("pointer");
    void change({ action: "add", symbol, ...add, ...(add.kind === "trend" ? { interval } : {}) });
  }, [change, symbol, interval]);
  const shown = useMemo(() => (view ? drawingsFor(view.drawings, symbol, interval) : []), [view, symbol, interval]);
  return { ready: view !== null, shown, tool, setTool, onDrawn, message, remove: (id: string) => void change({ action: "remove", id }),
    clear: () => void change({ action: "clear", symbol }) };
}

/** A point's candle: 01/10/2026 for daily, weekly and monthly bars, 01/10 09:00 for hourly ones (keyed by Hà Nội wall-clock seconds). */
export function when(t: string | number): string {
  if (typeof t === "string") return t.split("-").reverse().join("/");
  const iso = new Date(t * 1000).toISOString();
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)} ${iso.slice(11, 16)}`;
}

export function DrawingToolbar({ tools, symbol }: { tools: ReturnType<typeof useChartDrawings>; symbol: string }) {
  const { ready, tool, setTool, shown, clear } = tools;
  return (
    <div className="tb-draw" role="toolbar" aria-label="Công cụ vẽ">
      {TOOLS.map(([t, label, Icon]) => <button key={t} type="button" className={`btn ${tool === t ? "primary" : ""}`} aria-pressed={tool === t}
        disabled={!ready} onClick={() => setTool(tool === t ? "pointer" : t)}><Icon size={15} aria-hidden="true" />{label}</button>)}
      <button type="button" className="btn" disabled={!ready || shown.length === 0}
        onClick={() => { if (window.confirm(`Xóa mọi hình vẽ của ${symbol}?`)) clear(); }}><Trash2 size={15} aria-hidden="true" />Xóa hết</button>
      <span className="caption" role="status">{tool === "hline" ? "Bấm vào khung giá, hoặc kéo tới mức giá rồi thả."
        : tool === "trend" ? "Nhấn giữ ở điểm đầu, kéo tới điểm cuối rồi thả (Esc để hủy). Biểu đồ tạm không cuộn khi đang vẽ." : ""}</span>
    </div>
  );
}

export function DrawingList({ tools }: { tools: ReturnType<typeof useChartDrawings> }) {
  const { shown, remove, message } = tools;
  return <>
    {message && <p className="errors" role="alert">{message}</p>}
    {shown.length > 0 && <ul className="tb-alert-list" aria-label="Hình vẽ">
      {shown.map((d) => {
        const text = d.kind === "hline" ? `Đường ngang ${formatDecimal(d.price, 2)}`
          : `Đường xu hướng ${when(d.points![0].t)} ${formatDecimal(d.points![0].p, 2)} → ${when(d.points![1].t)} ${formatDecimal(d.points![1].p, 2)}`;
        return <li key={d.id}><span>{text}</span>
          <button className="btn" type="button" aria-label={`Xóa ${text}`} onClick={() => remove(d.id)}>Xóa</button></li>;
      })}
    </ul>}
  </>;
}
