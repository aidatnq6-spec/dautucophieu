"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ApiError, api } from "../lib/api";

type Sector = { key: string; name: string; count: number };
type Cell = { quarter: string; profit_yoy: string | null; profit_turn: string | null; cfo: string | null; debt_yoy: string | null };
type Total = { quarter: string; profit_yoy: string | null; profit_count: number; cfo: string | null; cfo_count: number; debt_yoy: string | null; debt_count: number };
type Now = { month: string; value: string; count: number; lowest_since: string | null; rank: string | null; months: number };
type Ticker = { symbol: string; pb: string; to_median: string; own_low: string | null; below_own_low: boolean | null; own_months: number };
type View = { key: string; name: string; members: string[]; financial: boolean;
  heatmap: { quarters: string[]; rows: { symbol: string; cells: Cell[] }[]; total: Total[] };
  valuation: { median: { month: string; value: string | null; count: number }[]; now: Now | null; tickers: Ticker[] } };
export type Layer = "profit" | "cfo" | "debt";

const LAYERS: { id: Layer; label: string }[] = [
  { id: "profit", label: "Lợi nhuận so cùng kỳ" }, { id: "cfo", label: "Dòng tiền kinh doanh (tỷ)" }, { id: "debt", label: "Nợ vay so cùng kỳ" }];
const DEFAULT = "bat-dong-san";
const qLabel = (p: string) => `Q${p.slice(-1)}/${p.slice(2, 4)}`;
const mLabel = (m: string) => `${m.slice(5, 7)}/${m.slice(0, 4)}`;
const pct = (v: string) => {
  const n = Math.round(Number(v) * 100);
  return `${n > 0 ? "+" : n < 0 ? "−" : ""}${Math.abs(n).toLocaleString("vi-VN")}%`;
};
const times = (v: string) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function growthTone(v: number, risingIsGood: boolean): string {
  const good = risingIsGood ? v > 0 : v < 0;
  const size = Math.abs(v) >= 0.5 ? 3 : Math.abs(v) >= 0.15 ? 2 : 1;
  return v === 0 ? "" : `${good ? "g" : "r"}${size}`;
}

/** What one heatmap cell shows and its colour (g1–g3 green, r1–r3 red). maxAbs: the ticker's largest cash flow in view, in đồng. */
export function cellView(layer: Layer, c: Cell, maxAbs: number): { text: string; tone: string } {
  if (layer === "profit") {
    if (c.profit_turn === "to_profit") return { text: "lãi lại", tone: "g2" };
    if (c.profit_turn === "to_loss") return { text: "lỗ", tone: "r3" };
    return c.profit_yoy === null ? { text: "—", tone: "" } : { text: pct(c.profit_yoy), tone: growthTone(Number(c.profit_yoy), true) };
  }
  if (layer === "debt") return c.debt_yoy === null ? { text: "—", tone: "" } : { text: pct(c.debt_yoy), tone: growthTone(Number(c.debt_yoy), false) };
  if (c.cfo === null) return { text: "—", tone: "" };
  const v = Number(c.cfo), share = maxAbs > 0 ? Math.abs(v) / maxAbs : 0;
  const size = share >= 0.66 ? 3 : share >= 0.33 ? 2 : 1;
  const text = `${v < 0 ? "−" : ""}${Math.round(Math.abs(v) / 1e9).toLocaleString("vi-VN")}`;
  return { text, tone: v === 0 ? "" : `${v > 0 ? "g" : "r"}${size}` };
}

function totalCell(layer: Layer, t: Total): { text: string; tone: string; title: string } {
  if (layer === "profit") return t.profit_yoy === null ? { text: "—", tone: "", title: "" }
    : { text: pct(t.profit_yoy), tone: growthTone(Number(t.profit_yoy), true), title: `${t.profit_count} mã có lãi cả hai kỳ` };
  if (layer === "debt") return t.debt_yoy === null ? { text: "—", tone: "", title: "" }
    : { text: pct(t.debt_yoy), tone: growthTone(Number(t.debt_yoy), false), title: `${t.debt_count} mã có số cả hai kỳ` };
  return t.cfo === null ? { text: "—", tone: "", title: "" }
    : { text: `${Number(t.cfo) < 0 ? "−" : ""}${Math.round(Math.abs(Number(t.cfo)) / 1e9).toLocaleString("vi-VN")}`, tone: Number(t.cfo) >= 0 ? "g1" : "r1", title: `${t.cfo_count} mã` };
}

/** The sector median's place in its own history. */
export function rankText(now: Now, first: string): string {
  const head = `P/B trung vị ${mLabel(now.month)}: ${times(now.value)} lần (${now.count} mã).`;
  const [y, m] = now.month.split("-").map(Number);
  const since = now.lowest_since && (() => { const [ly, lm] = now.lowest_since!.split("-").map(Number); return (y - ly) * 12 + (m - lm) >= 12; })();
  const rank = now.rank === null ? "" : ` ${since ? "chỉ" : "Chỉ"} ${Math.round(Number(now.rank) * 100)}% số tháng từ ${mLabel(first)} thấp hơn mức này.`;
  if (now.lowest_since === null) return `${head} Thấp nhất từ trước đến nay (từ ${mLabel(first)}).`;
  return since ? `${head} Thấp nhất kể từ ${mLabel(now.lowest_since)};${rank}` : `${head}${rank}`;
}

function MedianChart({ points }: { points: { month: string; value: string | null }[] }) {
  const known = points.filter((p) => p.value !== null) as { month: string; value: string }[];
  if (known.length < 2) return null;
  const W = 640, H = 160, pad = 24;
  const values = known.map((p) => Number(p.value)), lo = Math.min(...values), hi = Math.max(...values);
  const x = (i: number) => pad + (i * (W - 2 * pad)) / (known.length - 1);
  const y = (v: number) => H - pad - ((v - lo) * (H - 2 * pad)) / (hi - lo || 1);
  const path = known.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(Number(p.value)).toFixed(1)}`).join(" ");
  const last = known.at(-1)!;
  return (
    <svg className="sv-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`P/B trung vị của ngành từ ${mLabel(known[0].month)} đến ${mLabel(last.month)}`}>
      <line x1={pad} x2={W - pad} y1={y(Number(last.value))} y2={y(Number(last.value))} className="sv-now" />
      <path d={path} className="sv-line" />
      <text x={pad} y={pad - 8} className="sv-axis">{times(String(hi))}</text>
      <text x={pad} y={H - 6} className="sv-axis">{times(String(lo))} · {mLabel(known[0].month)}</text>
      <text x={W - pad} y={H - 6} className="sv-axis" textAnchor="end">{mLabel(last.month)}</text>
    </svg>
  );
}

export function SectorsView() {
  const params = useSearchParams(), router = useRouter(), path = usePathname();
  const [sectors, setSectors] = useState<Sector[] | null>(null);
  const [view, setView] = useState<View | null>(null);
  const [layer, setLayer] = useState<Layer>("profit");
  const [error, setError] = useState<string | null>(null);
  const wanted = params.get("nganh");
  const key = sectors ? (sectors.some((s) => s.key === wanted) ? wanted! : sectors.some((s) => s.key === DEFAULT) ? DEFAULT : sectors[0]?.key) : null;
  useEffect(() => { api<{ sectors: Sector[] }>("sectors").then((d) => setSectors(d.sectors), (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  useEffect(() => {
    if (!key) return;
    let live = true;
    api<View>(`sectors/${key}`).then((d) => { if (live) setView(d); }, (e) => { if (live) setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."); });
    return () => { live = false; };
  }, [key]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!sectors) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const choose = (k: string) => router.replace(`${path}?nganh=${k}`, { scroll: false });
  const h = view?.heatmap, v = view?.valuation;
  return (
    <>
      <div className="sv-pick">
        <label className="field">Ngành<select aria-label="Ngành" value={key ?? ""} onChange={(e) => choose(e.target.value)}>
          {sectors.map((s) => <option key={s.key} value={s.key}>{s.name} ({s.count} mã)</option>)}</select></label>
      </div>
      {!view || view.key !== key ? <p className="muted fx-loading" role="status">Đang tải ngành…</p> : <>
        <section className="surface" aria-label="Bản đồ nhiệt theo quý">
          <h2>Bản đồ nhiệt theo quý: {view.name}</h2>
          <div className="sv-layers" role="radiogroup" aria-label="Lớp số liệu">
            {LAYERS.map((l) => <label key={l.id} className={layer === l.id ? "on" : undefined}>
              <input type="radio" name="sv-layer" checked={layer === l.id} onChange={() => setLayer(l.id)}
                disabled={view.financial && l.id !== "profit"} />{l.label}</label>)}
          </div>
          {view.financial && <p className="caption">Ngân hàng, chứng khoán và bảo hiểm có mẫu báo cáo riêng: chỉ có lớp lợi nhuận.</p>}
          {h && h.quarters.length > 0 ? <div className="tablewrap"><table className="sv-heat" aria-label={`Bản đồ nhiệt ${view.name}`}>
            <thead><tr><th>Mã</th>{h.quarters.map((p) => <th key={p} className="num">{qLabel(p)}</th>)}</tr></thead>
            <tbody>
              {h.rows.map((r) => {
                const maxAbs = Math.max(0, ...r.cells.map((c) => Math.abs(Number(c.cfo ?? 0))));
                return <tr key={r.symbol}><th scope="row"><Link href={`/research/${r.symbol}`}>{r.symbol}</Link></th>
                  {r.cells.map((c) => { const cv = cellView(layer, c, maxAbs); return <td key={c.quarter} className={`num sv-${cv.tone || "none"}`}>{cv.text}</td>; })}</tr>;
              })}
              <tr className="sv-total"><th scope="row">Cả ngành</th>
                {h.total.map((t) => { const tv = totalCell(layer, t); return <td key={t.quarter} className={`num sv-${tv.tone || "none"}`} title={tv.title}>{tv.text}</td>; })}</tr>
            </tbody>
          </table></div> : <p className="muted">Chưa có báo cáo quý của các mã trong ngành này.</p>}
          <p className="caption">Mỗi ô so với cùng quý năm trước (lợi nhuận công ty mẹ, nợ vay ngắn + dài hạn) hoặc là dòng tiền kinh doanh của quý (tỷ đồng, đậm
            hơn ở quý lớn của chính mã đó). Xanh là tốt cho doanh nghiệp: lãi tăng, tiền vào, nợ giảm; đỏ ngược lại. Cùng kỳ lỗ thì không tính được tăng trưởng:
            ô ghi lãi lại hoặc lỗ. Dòng Cả ngành cộng các mã có số cả hai kỳ. Không phải khuyến nghị.</p>
        </section>
        <section className="surface" aria-label="Định giá ngành">
          <h2>Định giá ngành: {view.name}</h2>
          {v?.now ? <>
            <p data-testid="sector-rank">{rankText(v.now, v.median.find((m) => m.value !== null)!.month)}</p>
            <MedianChart points={v.median} />
            <table className="fv-table" aria-label={`P/B từng mã ${view.name}`}>
              <thead><tr><th>Mã</th><th className="num">P/B</th><th className="num">So với trung vị ngành</th><th className="num">Thấp nhất 5 năm trước của mã</th><th>Ghi chú</th></tr></thead>
              <tbody>{v.tickers.map((t) => <tr key={t.symbol}>
                <td data-label="Mã"><Link href={`/research/${t.symbol}`}>{t.symbol}</Link></td>
                <td className="num" data-label="P/B">{times(t.pb)}</td>
                <td className="num" data-label="So với trung vị ngành">{Math.round(Number(t.to_median) * 100).toLocaleString("vi-VN")}%</td>
                <td className="num" data-label="Thấp nhất 5 năm trước">{t.own_low === null ? "—" : times(t.own_low)}</td>
                <td data-label="Ghi chú">{t.below_own_low && <span className="pill good">Bằng hoặc dưới đáy 5 năm</span>}</td>
              </tr>)}</tbody>
            </table>
          </> : <p className="muted">Chưa đủ số: cần ít nhất 3 mã có P/B trong cùng tháng.</p>}
          <p className="caption">P/B mỗi tháng = giá đóng cửa cuối tháng × số cổ phiếu ÷ vốn chủ của báo cáo đã công bố (như trang Định giá). Trung vị không bị một mã
            rất lớn kéo lệch như cách cộng theo vốn hóa, nên không cần bỏ mã chi phối. P/B thấp là rẻ so với sổ sách, chưa phải là đáng mua: đọc cùng bản đồ nhiệt
            và nợ vay. Không phải khuyến nghị.</p>
        </section>
      </>}
    </>
  );
}
