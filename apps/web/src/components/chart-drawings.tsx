"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Minus, MousePointer2, Spline, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal } from "../lib/format";

export type Interval = "1D" | "1H";
export type Point = { t: string | number; p: string };
export type Drawing = { id: string; symbol: string; kind: "hline" | "trend"; interval: Interval | null; price: string | null;
  points: [Point, Point] | null; created_at: string };
export type Tool = "pointer" | "hline" | "trend";
type View = { version: number; drawings: Drawing[] };
type Add = { kind: "hline"; price: string } | { kind: "trend"; points: [Point, Point] };

/** A level shows on both frames; a trend line only on the frame it was drawn on (daily and hourly bars are keyed differently). */
export function drawingsFor(drawings: Drawing[], symbol: string, interval: Interval): Drawing[] {
  return drawings.filter((d) => d.symbol === symbol && (d.kind === "hline" || d.interval === interval));
}

/** The cursor's price, two decimals, as a plain decimal for the API; null when it is not a positive price. */
export function roundPrice(p: number): string | null {
  if (!Number.isFinite(p)) return null;
  const rounded = Math.round(p * 100) / 100;
  return rounded > 0 ? String(rounded) : null;
}

/** One click on the price pane: a level is drawn at once, a trend line waits for a second click on another candle. */
export function clickStep(tool: Tool, pending: Point | null, at: { t: string | number; p: number }): { pending: Point | null; add: Add | null } {
  const p = roundPrice(at.p);
  if (tool === "pointer" || p === null) return { pending, add: null };
  if (tool === "hline") return { pending: null, add: { kind: "hline", price: p } };
  if (pending === null || pending.t === at.t) return { pending: pending ?? { t: at.t, p }, add: null };
  return { pending: null, add: { kind: "trend", points: [pending, { t: at.t, p }] } };
}

const TOOLS: [Tool, string, typeof Minus][] = [["pointer", "Con trỏ", MousePointer2], ["hline", "Đường ngang", Minus], ["trend", "Đường xu hướng", Spline]];

/** Hình vẽ: the owner's levels and trend lines for the ticker and frame shown, kept in the personal store. */
export function useChartDrawings(symbol: string, interval: Interval) {
  const [view, setView] = useState<View | null>(null);
  const [tool, setTool] = useState<Tool>("pointer");
  // The first point of a trend line belongs to the ticker, frame and tool it was clicked with; switching any of them drops it.
  const key = `${symbol}|${interval}|${tool}`;
  const [held, setHeld] = useState<{ key: string; point: Point | null }>({ key, point: null });
  const pending = held.key === key ? held.point : null;
  const setPending = useCallback((point: Point | null) => setHeld({ key, point }), [key]);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("trend/drawings").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải hình vẽ.")); }, []);
  useEffect(() => {
    if (pending === null) return;
    const cancel = (e: KeyboardEvent) => { if (e.key === "Escape") setPending(null); };
    window.addEventListener("keydown", cancel);
    return () => window.removeEventListener("keydown", cancel);
  }, [pending, setPending]);

  const change = useCallback(async (body: Record<string, unknown>) => {
    if (!view) return;
    try {
      setView(await api<View>("trend/drawings", { method: "PUT", body: { ...body, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu hình vẽ.");
    }
  }, [view]);
  const onPoint = useCallback((at: { t: string | number; p: number }) => {
    const step = clickStep(tool, pending, at);
    setPending(step.pending);
    if (step.add) void change({ action: "add", symbol, ...step.add, ...(step.add.kind === "trend" ? { interval } : {}) });
  }, [tool, pending, setPending, change, symbol, interval]);
  const shown = useMemo(() => (view ? drawingsFor(view.drawings, symbol, interval) : []), [view, symbol, interval]);
  return { ready: view !== null, shown, tool, setTool, pending, onPoint, message, remove: (id: string) => void change({ action: "remove", id }),
    clear: () => void change({ action: "clear", symbol }) };
}

/** A point's candle: 01/10/2026 for daily bars, 01/10 09:00 for hourly ones (keyed by Hà Nội wall-clock seconds). */
export function when(t: string | number): string {
  if (typeof t === "string") return t.split("-").reverse().join("/");
  const iso = new Date(t * 1000).toISOString();
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)} ${iso.slice(11, 16)}`;
}

export function DrawingToolbar({ tools, symbol }: { tools: ReturnType<typeof useChartDrawings>; symbol: string }) {
  const { ready, tool, setTool, pending, shown, clear } = tools;
  return (
    <div className="tb-draw" role="toolbar" aria-label="Công cụ vẽ">
      {TOOLS.map(([t, label, Icon]) => <button key={t} type="button" className={`btn ${tool === t ? "primary" : ""}`} aria-pressed={tool === t}
        disabled={!ready} onClick={() => setTool(tool === t ? "pointer" : t)}><Icon size={15} aria-hidden="true" />{label}</button>)}
      <button type="button" className="btn" disabled={!ready || shown.length === 0}
        onClick={() => { if (window.confirm(`Xóa mọi hình vẽ của ${symbol}?`)) clear(); }}><Trash2 size={15} aria-hidden="true" />Xóa hết</button>
      <span className="caption" role="status">{tool === "hline" ? "Bấm vào khung giá để đặt đường ngang."
        : tool === "trend" ? (pending ? `Điểm đầu ${when(pending.t)} ở ${formatDecimal(pending.p, 2)}; bấm điểm thứ hai (Esc để hủy).`
          : "Bấm điểm đầu trên khung giá.") : ""}</span>
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
