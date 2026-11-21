"use client";
import { fit, squarify } from "./asset-views";

type Missing = { status: "missing"; reason: string };
type Pull = { symbol: string; points: string; held: boolean };
export type Impact = { status: "ok"; computed: string; actual: string; up: Pull[]; down: Pull[] } | Missing;
export type HeatRow = { symbol: string; sector: string | null; pct: string; value_mn: string; held: boolean };
export type HeatMap = { status: "ok"; rows: HeatRow[] } | Missing;

const num = (v: number, d: number) => v.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
const signed = (v: number, d: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${num(Math.abs(v), d)}`;

/** The colour step of a session change: 1 under 1%, 2 under 3%, 3 from 3% (near the ±7% band); grey when unchanged. */
export function dayTone(pct: string): string {
  const v = Number(pct), a = Math.abs(v);
  return v === 0 ? "am-flat" : `am-${v > 0 ? "g" : "r"}${a >= 0.03 ? 3 : a >= 0.01 ? 2 : 1}`;
}

/** Sectors (largest matched value first), each with its stocks, for the two-level map. */
export function sectorGroups(rows: HeatRow[]): { sector: string; value: number; rows: HeatRow[] }[] {
  const by = new Map<string, HeatRow[]>();
  for (const r of rows) by.set(r.sector ?? "Khác", [...(by.get(r.sector ?? "Khác") ?? []), r]);
  return [...by.entries()].map(([sector, rs]) => ({ sector, value: rs.reduce((a, r) => a + Number(r.value_mn), 0),
    rows: [...rs].sort((a, b) => Number(b.value_mn) - Number(a.value_mn)) })).sort((a, b) => b.value - a.value);
}

function Bars({ rows, max, side }: { rows: Pull[]; max: number; side: "up" | "down" }) {
  return (
    <ul className="im-bars" aria-label={side === "up" ? "Mã kéo lên" : "Mã kéo xuống"}>{rows.map((r) => (
      <li key={r.symbol}>
        <span className="im-sym">{r.symbol}{r.held && <span className="pill good"> đang nắm</span>}</span>
        <span className="im-track"><span className={`im-bar im-${side}`} style={{ width: `${(Math.abs(Number(r.points)) / max) * 100}%` }} /></span>
        <span className={`im-pts ${side === "up" ? "positive" : "negative"}`}>{signed(Number(r.points), 2)}</span>
      </li>))}
    </ul>
  );
}

/** Tác động lên VN-Index: the ten stocks that pulled the index most each way, in points, from shares outstanding and closing prices. */
export function ImpactView({ impact }: { impact: Impact | undefined }) {
  if (!impact) return null;
  if (impact.status !== "ok") return <section aria-label="Tác động lên VN-Index"><h3>Tác động lên VN-Index</h3>
    <p className="muted">Chưa có số liệu ({impact.reason}).</p></section>;
  const max = Math.max(...[...impact.up, ...impact.down].map((r) => Math.abs(Number(r.points))), 0.01);
  return (
    <section aria-label="Tác động lên VN-Index" data-testid="impact">
      <h3>Tác động lên VN-Index</h3>
      <div className="im-grid">
        <div><p className="caption">Kéo lên</p><Bars rows={impact.up} max={max} side="up" /></div>
        <div><p className="caption">Kéo xuống</p><Bars rows={impact.down} max={max} side="down" /></div>
      </div>
      <p className="caption">Điểm ước tính theo vốn hóa (số cổ phiếu lưu hành VNDirect × giá), toàn bộ mã HOSE. Tổng các mã {signed(Number(impact.computed), 2)} điểm,
        VN-Index thực tế {signed(Number(impact.actual), 2)} điểm; chỉ hiện khi hai số khớp. Không phải khuyến nghị.</p>
    </section>
  );
}

/** Bản đồ nhiệt phiên: every traded HOSE stock as a cell sized by its matched value, grouped by sector, coloured by its change. */
export function HeatMapView({ heatmap }: { heatmap: HeatMap | undefined }) {
  if (!heatmap) return null;
  if (heatmap.status !== "ok") return <section aria-label="Bản đồ nhiệt phiên"><h3>Bản đồ nhiệt phiên</h3>
    <p className="muted">Chưa có số liệu ({heatmap.reason}).</p></section>;
  const W = 960, H = 480, groups = sectorGroups(heatmap.rows);
  const boxes = squarify(groups.map((g) => g.value), W, H);
  return (
    <section aria-label="Bản đồ nhiệt phiên" data-testid="heatmap">
      <h3>Bản đồ nhiệt phiên</h3>
      <svg className="hm" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Bản đồ nhiệt các mã HOSE theo ngành">
        {groups.map((g, i) => {
          const b = boxes[i], head = b.h > 40 && b.w > 60 ? 14 : 0;
          const cells = squarify(g.rows.map((r) => Number(r.value_mn)), b.w, b.h - head, b.x, b.y + head);
          return (
            <g key={g.sector}>
              {head > 0 && <text x={b.x + 4} y={b.y + 11} className="hm-sector">{fit(g.sector, b.w, 6.2)}</text>}
              {g.rows.map((r, j) => {
                const c = cells[j], big = c.w > 34 && c.h > 22;
                return (
                  <g key={r.symbol}>
                    <rect x={c.x} y={c.y} width={c.w} height={c.h} className={`am-tile ${dayTone(r.pct)}${r.held ? " hm-held" : ""}`}>
                      <title>{`${r.symbol} ${signed(Number(r.pct) * 100, 2)}% · ${num(Number(r.value_mn) / 1000, 1)} tỷ${r.held ? " · đang nắm" : ""}`}</title>
                    </rect>
                    {big && <text x={c.x + c.w / 2} y={c.y + c.h / 2 - (c.h > 36 ? 3 : -4)} className="hm-sym">{r.symbol}</text>}
                    {big && c.h > 36 && <text x={c.x + c.w / 2} y={c.y + c.h / 2 + 11} className="hm-pct">{signed(Number(r.pct) * 100, 2)}%</text>}
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
      <p className="caption">Mỗi ô là một mã HOSE có giao dịch, cỡ ô theo giá trị khớp lệnh, màu theo mức tăng giảm (đậm dần ở 1% và 3%); viền đậm là mã đang
        nắm. Rê chuột vào ô để xem số. Không phải khuyến nghị.</p>
    </section>
  );
}
