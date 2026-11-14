"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Tile = { id: string; label: string; note: string | null; value: string; change: string | null };
type Group = { id: string; label: string; value: string; tiles: Tile[] };
type AssetMap = { groups: Group[]; total: string; unpriced: string[] };
type Step = { id: string; amount: string; symbol?: string };
type Bridge = { status: "ok"; month: string; start_day: string | null; end_day: string; start: string; end: string; other: string; steps: Step[] }
  | { status: "missing_prices"; month: string; missing: string[]; start_day: string | null; end_day: string }
  | { status: "no_sessions"; month: string };
type BookPart = { status: "ok"; start: string; end: string; steps: Step[] } | { status: "missing_prices"; missing: string[]; start_day: string | null; end_day: string };
type BridgeData = { months: string[]; bridge: Bridge | null; book?: BookPart | null };
export type Rect = { x: number; y: number; w: number; h: number };

/** Squarified treemap (Bruls, Huizing, van Wijk): rectangles for values (largest first) filling w × h, each as close to square as
 * the row allows. Returns one rectangle per value, in the order given. */
export function squarify(values: number[], w: number, h: number, x0 = 0, y0 = 0): Rect[] {
  const total = values.reduce((a, b) => a + b, 0);
  const out: Rect[] = new Array(values.length);
  if (total <= 0 || w <= 0 || h <= 0) return values.map(() => ({ x: x0, y: y0, w: 0, h: 0 }));
  const scale = (w * h) / total;
  const order = values.map((v, i) => ({ i, a: v * scale })).filter((o) => o.a > 0);
  let x = x0, y = y0, rw = w, rh = h, row: typeof order = [];
  const worst = (r: typeof order, side: number) => {
    const s = r.reduce((a, o) => a + o.a, 0), mx = Math.max(...r.map((o) => o.a)), mn = Math.min(...r.map((o) => o.a));
    return Math.max((side * side * mx) / (s * s), (s * s) / (side * side * mn));
  };
  const lay = (r: typeof order) => {
    const s = r.reduce((a, o) => a + o.a, 0);
    if (rw >= rh) {  // a column on the left
      const cw = s / rh; let cy = y;
      for (const o of r) { const ch = o.a / cw; out[o.i] = { x, y: cy, w: cw, h: ch }; cy += ch; }
      x += cw; rw -= cw;
    } else {  // a row on top
      const ch = s / rw; let cx = x;
      for (const o of r) { const cw = o.a / ch; out[o.i] = { x: cx, y, w: cw, h: ch }; cx += cw; }
      y += ch; rh -= ch;
    }
  };
  for (const o of order) {
    const side = Math.min(rw, rh);
    if (row.length && worst([...row, o], side) > worst(row, side)) { lay(row); row = []; }
    row.push(o);
  }
  if (row.length) lay(row);
  values.forEach((v, i) => { if (!out[i]) out[i] = { x: x0, y: y0, w: 0, h: 0 }; });
  return out;
}

/** Tile colour from the gain on cost: green up, red down, three steps; grey when there is no market price. */
export function changeTone(change: string | null): string {
  if (change === null) return "am-none";
  const v = Number(change), size = Math.abs(v) >= 0.2 ? 3 : Math.abs(v) >= 0.05 ? 2 : 1;
  return v === 0 ? "am-flat" : `am-${v > 0 ? "g" : "r"}${size}`;
}

const pct = (v: string | null) => (v === null ? "" : `${Number(v) > 0 ? "+" : ""}${formatRatio(v, 1)}`);
const millions = (v: string) => `${(Number(v) / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tr`;

export function AssetMapView() {
  const [map, setMap] = useState<AssetMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [list, setList] = useState(false);
  useEffect(() => { api<AssetMap>("asset-map").then(setMap, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const W = 960, H = 440;
  const groups = map?.groups ?? [];
  const boxes = squarify(groups.map((g) => Number(g.value)), W, H);
  return (
    <section className="surface" aria-label="Bản đồ danh mục">
      <h2>Bản đồ danh mục</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!map && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {map && (groups.length === 0 ? <p className="muted">Chưa có tài sản nào trong sổ lệnh và Sổ tài sản.</p> : <>
        <div className="sv-layers" role="radiogroup" aria-label="Cách xem bản đồ">
          {[[false, "Bản đồ"], [true, "Danh sách"]].map(([v, label]) => <label key={String(v)} className={list === v ? "on" : undefined}>
            <input type="radio" name="am-view" checked={list === v} onChange={() => setList(v as boolean)} />{label as string}</label>)}
        </div>
        {!list ? <svg className="am-map" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Bản đồ danh mục, tổng ${formatVnd(map.total)}`}>
          {groups.map((g, gi) => {
            const b = boxes[gi], head = b.h > 60 && b.w > 90 ? 20 : 0;
            const tiles = squarify(g.tiles.map((t) => Number(t.value)), b.w - 2, b.h - head - 2, b.x + 1, b.y + head + 1);
            return <g key={g.id}>
              <rect x={b.x} y={b.y} width={b.w} height={b.h} className="am-group" />
              {head > 0 && <text x={b.x + 6} y={b.y + 14} className="am-head">{g.label} · {formatRatio(String(Number(g.value) / Number(map.total)), 0)}</text>}
              {g.tiles.map((t, ti) => { const r = tiles[ti]; const big = r.w > 64 && r.h > 34;
                return <g key={t.id}><rect x={r.x} y={r.y} width={r.w} height={r.h} className={`am-tile ${changeTone(t.change)}`}>
                  <title>{`${g.label} · ${t.label}${t.note ? ` (${t.note})` : ""}: ${formatVnd(t.value)}${t.change !== null ? `, ${pct(t.change)} so với vốn` : ""}`}</title></rect>
                  {big && <text x={r.x + 5} y={r.y + 15} className="am-label">{t.label}</text>}
                  {big && r.h > 50 && <text x={r.x + 5} y={r.y + 30} className="am-sub">{millions(t.value)}{t.change !== null ? ` · ${pct(t.change)}` : ""}</text>}</g>;
              })}
            </g>;
          })}
        </svg> : <table className="fv-table" aria-label="Danh sách tài sản theo lớp">
          <thead><tr><th>Lớp</th><th>Tài sản</th><th className="num">Giá trị</th><th className="num">Tỷ trọng</th><th className="num">So với vốn</th></tr></thead>
          <tbody>{groups.flatMap((g) => g.tiles.map((t) => <tr key={t.id}><td data-label="Lớp">{g.label}</td>
            <td data-label="Tài sản">{t.label}{t.note && <div className="caption">{t.note}</div>}</td>
            <td className="num" data-label="Giá trị">{formatVnd(t.value)}</td>
            <td className="num" data-label="Tỷ trọng">{formatRatio(String(Number(t.value) / Number(map.total)), 1)}</td>
            <td className="num" data-label="So với vốn">{pct(t.change) || "—"}</td></tr>))}</tbody>
        </table>}
        <p className="caption">Diện tích ô = giá trị (tổng {formatVnd(map.total)}). Màu = lãi/lỗ so với vốn khi có giá thị trường (cổ phiếu theo giá đóng cửa gần
          nhất, quỹ theo NAV, vàng theo giá mua vào); ô xám là tài sản tính theo số đã nhập. Chưa gồm bất động sản.
          {map.unpriced.length ? ` Chưa có giá, không vẽ: ${map.unpriced.join(", ")}.` : ""}</p>
      </>)}
    </section>
  );
}

const NAMES: Record<string, string> = { flows: "Tiền nộp/rút", dividends: "Cổ tức tiền", costs: "Phí và thuế giao dịch", "book:fund_price": "Giá quỹ",
  "book:gold_price": "Giá vàng", "book:entries": "Sổ tài sản: ghi thêm/bớt/sửa" };
const STEP_LABEL = (s: Step) => (s.symbol ? s.symbol : NAMES[s.id] ?? s.id);
const MAX_TICKERS = 8;

/** Steps as drawn: money in/out first, the largest tickers, the rest of the tickers together, then dividends, costs and anything left. */
export function bridgeBars(b: Extract<Bridge, { status: "ok" }>, book?: Extract<BookPart, { status: "ok" }> | null): { label: string; amount: number; kind: "total" | "step" }[] {
  const tickers = b.steps.filter((s) => s.symbol), shown = tickers.slice(0, MAX_TICKERS), rest = tickers.slice(MAX_TICKERS);
  const bars: { label: string; amount: number; kind: "total" | "step" }[] = [{ label: b.start_day ? "Đầu tháng" : "Bắt đầu",
    amount: Number(b.start) + (book ? Number(book.start) : 0), kind: "total" }];
  for (const s of b.steps.filter((x) => x.id === "flows")) bars.push({ label: STEP_LABEL(s), amount: Number(s.amount), kind: "step" });
  for (const s of shown) bars.push({ label: STEP_LABEL(s), amount: Number(s.amount), kind: "step" });
  if (rest.length) bars.push({ label: `${rest.length} mã khác`, amount: rest.reduce((a, s) => a + Number(s.amount), 0), kind: "step" });
  for (const s of b.steps.filter((x) => x.id === "dividends" || x.id === "costs")) bars.push({ label: STEP_LABEL(s), amount: Number(s.amount), kind: "step" });
  if (Number(b.other) !== 0) bars.push({ label: "Khác", amount: Number(b.other), kind: "step" });
  for (const s of book?.steps ?? []) bars.push({ label: STEP_LABEL(s), amount: Number(s.amount), kind: "step" });
  bars.push({ label: "Cuối kỳ", amount: Number(b.end) + (book ? Number(book.end) : 0), kind: "total" });
  return bars;
}

/** "Điểm cần soi": the three largest causes other than money in and out. */
export function bridgeNotes(b: Extract<Bridge, { status: "ok" }>, book?: Extract<BookPart, { status: "ok" }> | null): string[] {
  const causes = [...b.steps, ...(book?.steps ?? [])].filter((s) => s.id !== "flows" && s.id !== "book:entries").sort((x, y) => Math.abs(Number(y.amount)) - Math.abs(Number(x.amount))).slice(0, 3);
  return causes.map((s) => `${STEP_LABEL(s)} ${Number(s.amount) > 0 ? "đóng góp" : "làm giảm"} ${formatVnd(s.amount.replace("-", ""))}`);
}

/** Each bar's [from, to]: a total stands on zero; a step starts where the bars before it ended. */
export function barSpans(bars: { amount: number; kind: "total" | "step" }[]): [number, number][] {
  return bars.reduce<[number, number][]>((acc, b) => {
    const level = acc.length ? acc[acc.length - 1][1] : 0;
    return [...acc, b.kind === "total" ? [0, b.amount] : [level, level + b.amount]];
  }, []);
}

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

function Waterfall({ bars }: { bars: ReturnType<typeof bridgeBars> }) {
  const W = 960, H = 300, top = 18, bottom = 64, left = 8, gap = 8;
  const spans = barSpans(bars);
  const lo = Math.min(0, ...spans.flat()), hi = Math.max(...spans.flat(), 1);
  const y = (v: number) => top + ((hi - v) * (H - top - bottom)) / (hi - lo || 1);
  const bw = (W - left * 2) / bars.length - gap;
  return (
    <svg className="am-fall" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Thác nước thay đổi tài sản trong tháng">
      {bars.map((b, i) => { const [a, c] = spans[i], x = left + i * (bw + gap), y1 = y(Math.max(a, c)), y2 = y(Math.min(a, c));
        const cls = b.kind === "total" ? "am-total" : b.amount >= 0 ? "am-up" : "am-down";
        return <g key={`${b.label}-${i}`}>
          <rect x={x} y={y1} width={bw} height={Math.max(1, y2 - y1)} className={cls}><title>{`${b.label}: ${formatVnd(String(Math.round(b.amount)))}`}</title></rect>
          <text x={x + bw / 2} y={y1 - 4} textAnchor="middle" className="am-sub">{b.kind === "step" && b.amount > 0 ? "+" : ""}{millions(String(b.amount))}</text>
          <text x={x + bw / 2} y={H - bottom + 16} textAnchor="middle" className="am-axis">{b.label.length > 14 ? `${b.label.slice(0, 13)}…` : b.label}</text>
        </g>; })}
      <line x1={left} x2={W - left} y1={y(0)} y2={y(0)} className="am-zero" />
    </svg>
  );
}

export function MonthBridgeView() {
  const [data, setData] = useState<BridgeData | null>(null);
  const [month, setMonth] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api<BridgeData>(`month-bridge${month ? `?month=${month}` : ""}`)
      .then((d) => { if (live) setData(d); }, (e) => { if (live) setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."); });
    return () => { live = false; };
  }, [month]);
  const b = data?.bridge;
  const book = data?.book?.status === "ok" ? data.book : null;
  return (
    <section className="surface" aria-label="Vì sao tài sản tháng này thay đổi">
      <h2>Vì sao tài sản tháng này thay đổi?</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!data && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {data && (data.months.length === 0 ? <p className="muted">Chưa có giao dịch nào trong sổ lệnh.</p> : <>
        <label className="field sv-pick">Tháng<select aria-label="Tháng" value={month ?? data.months[0]} onChange={(e) => setMonth(e.target.value)}>
          {data.months.map((m) => <option key={m} value={m}>{m.slice(5)}/{m.slice(0, 4)}</option>)}</select></label>
        {b?.status === "missing_prices" && <p className="notice" role="note">Chưa tính được: thiếu giá đóng cửa của {b.missing.join(", ")} ngày
          {b.start_day ? ` ${dmy(b.start_day)} hoặc` : ""} {dmy(b.end_day)}. Không tự điền giá.</p>}
        {b?.status === "no_sessions" && <p className="muted">Tháng này chưa có phiên nào có giá.</p>}
        {b?.status === "ok" && <>
          <p data-testid="bridge-summary">Tài khoản chứng khoán {b.start_day ? `từ ${formatVnd(b.start)} (đóng cửa ${dmy(b.start_day)})` : "từ 0"} lên {formatVnd(b.end)}
            {" "}(đóng cửa {dmy(b.end_day)}): {Number(b.end) - Number(b.start) >= 0 ? "tăng" : "giảm"} {formatVnd(String(Math.abs(Number(b.end) - Number(b.start))))}.</p>
          {book && <p data-testid="book-summary">Sổ tài sản từ {formatVnd(book.start)} lên {formatVnd(book.end)}; cộng cả hai: {formatVnd(String(Number(b.start)
            + Number(book.start)))} → {formatVnd(String(Number(b.end) + Number(book.end)))}.</p>}
          {data?.book?.status === "missing_prices" && <p className="notice" role="note" data-testid="book-missing">Sổ tài sản chưa cộng vào tháng này: chưa có
            giá ngày {data.book.start_day ? dmy(data.book.start_day) : "đầu kỳ"} của {data.book.missing.join(", ")} (lịch sử NAV quỹ lưu từ 14/11/2026, giá vàng
            từ 14/11/2026). Không tự điền giá; thác nước dưới đây chỉ gồm tài khoản chứng khoán.</p>}
          <Waterfall bars={bridgeBars(b, book)} />
          {bridgeNotes(b, book).length > 0 && <div className="notice" role="note" data-testid="bridge-notes"><strong>Điểm cần soi:</strong>
            <ul>{bridgeNotes(b, book).map((n) => <li key={n}>{n}</li>)}</ul></div>}
          <table className="fv-table" aria-label="Các khoản thay đổi trong tháng">
            <thead><tr><th>Khoản</th><th className="num">Số tiền</th></tr></thead>
            <tbody>{b.steps.map((s) => <tr key={s.id}><td data-label="Khoản">{STEP_LABEL(s)}</td><td className="num" data-label="Số tiền">{formatVnd(s.amount)}</td></tr>)}
              {Number(b.other) !== 0 && <tr><td data-label="Khoản">Khác (chưa phân loại)</td><td className="num" data-label="Số tiền">{formatVnd(b.other)}</td></tr>}
              {book?.steps.map((s) => <tr key={s.id}><td data-label="Khoản">{STEP_LABEL(s)}</td><td className="num" data-label="Số tiền">{formatVnd(s.amount)}</td></tr>)}</tbody>
          </table>
        </>}
        <p className="caption">Tài khoản chứng khoán = tiền + cổ phiếu (cả cổ phiếu chờ về) theo giá đóng cửa. Mỗi mã = giá trị cuối kỳ − giá trị đầu kỳ − tiền mua + tiền
          bán, chưa trừ phí; phí và thuế tách riêng. Cộng các khoản đúng bằng thay đổi; phần lệch (nếu có) hiện ở dòng Khác, không chia vào khoản nào. Sổ tài sản lấy
          đúng bản đã lưu đến hết mỗi ngày: Giá quỹ = số đơn vị đầu kỳ × chênh lệch NAV, Giá vàng = số chỉ đầu kỳ × chênh lệch giá mua vào; còn lại (thêm, bớt, sửa
          dòng, kể cả tiền chuyển qua lại với tài khoản chứng khoán) ở dòng Sổ tài sản: ghi thêm/bớt/sửa. Chưa gồm bất động sản.</p>
      </>)}
    </section>
  );
}
