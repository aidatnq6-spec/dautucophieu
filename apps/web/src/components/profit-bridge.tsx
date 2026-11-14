"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal } from "../lib/format";
import { type Bar, Waterfall } from "./asset-views";

type Step = { id: string; amount: string };
type Bridge = { status: "ok"; quarter: string; base_quarter: string; start: string; end: string; margins: { base: string; now: string }; steps: Step[]; other: string }
  | { status: "no_base" | "missing_lines"; quarter: string; missing?: string[] };
type View = { symbol: string; financial: boolean; quarters: string[]; bridge: Bridge | null };

const LABEL: Record<string, string> = { revenue: "Doanh thu", margin: "Biên gộp", selling: "Chi phí bán hàng", admin: "Chi phí quản lý",
  financial: "Tài chính (thu − chi)", associates: "Công ty liên kết", other_profit: "Lợi nhuận khác", tax: "Thuế", minority: "Cổ đông thiểu số" };
const ql = (q: string) => `Q${q.slice(-1)}/${q.slice(0, 4)}`;
const ty = (v: string) => `${Number(v) < 0 ? "−" : ""}${formatDecimal(String(Math.abs(Number(v)) / 1e9), 1)} tỷ`;

/** Bars from last year's quarter to this one; zero steps are left out, a gap no line explains is its own bar. */
export function profitBars(b: Extract<Bridge, { status: "ok" }>): Bar[] {
  const bars: Bar[] = [{ label: ql(b.base_quarter), amount: Number(b.start), kind: "total" }];
  for (const s of b.steps) if (Number(s.amount) !== 0) bars.push({ label: LABEL[s.id] ?? s.id, amount: Number(s.amount), kind: "step" });
  if (Number(b.other) !== 0) bars.push({ label: "Khác (chưa khớp dòng)", amount: Number(b.other), kind: "step" });
  bars.push({ label: ql(b.quarter), amount: Number(b.end), kind: "total" });
  return bars;
}

/** The two largest pushes up and down, as a sentence each. */
export function profitNotes(b: Extract<Bridge, { status: "ok" }>): string[] {
  const steps = b.steps.filter((s) => Number(s.amount) !== 0);
  const up = [...steps].sort((x, y) => Number(y.amount) - Number(x.amount)).filter((s) => Number(s.amount) > 0).slice(0, 2);
  const down = [...steps].sort((x, y) => Number(x.amount) - Number(y.amount)).filter((s) => Number(s.amount) < 0).slice(0, 2);
  return [...up.map((s) => `${LABEL[s.id]} kéo lên ${ty(s.amount)}`), ...down.map((s) => `${LABEL[s.id]} kéo xuống ${ty(s.amount.replace("-", ""))}`)];
}

export function ProfitBridge({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [quarter, setQuarter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api<View>(`stock/${encodeURIComponent(symbol)}/profit-bridge${quarter ? `/${quarter}` : ""}`)
      .then((v) => { if (live) setView(v); }, (e) => { if (live) setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."); });
    return () => { live = false; };
  }, [symbol, quarter]);
  if (error || !view || view.financial) return null;  // banks, brokers and insurers report another layout
  const b = view.bridge;
  return (
    <section className="surface" aria-label="Vì sao lợi nhuận quý thay đổi">
      <h2>Vì sao lợi nhuận quý thay đổi?</h2>
      {view.quarters.length === 0 ? <p className="muted">Chưa có quý nào có cả cùng kỳ năm trước.</p> : <>
        <label className="field sv-pick">Quý<select aria-label="Quý" value={quarter ?? view.quarters[0]} onChange={(e) => setQuarter(e.target.value)}>
          {view.quarters.map((q) => <option key={q} value={q}>{ql(q)}</option>)}</select></label>
        {b?.status === "missing_lines" && <p className="muted">Báo cáo quý này thiếu dòng {b.missing?.join(", ")}: chưa tách được.</p>}
        {b?.status === "ok" && <>
          <p data-testid="profit-summary">Lợi nhuận sau thuế của cổ đông công ty mẹ {ql(b.quarter)}: {ty(b.end)}, so với {ty(b.start)} {ql(b.base_quarter)}.
            Biên gộp {formatDecimal(String(Number(b.margins.base) / 100), 1)}% → {formatDecimal(String(Number(b.margins.now) / 100), 1)}%.</p>
          <Waterfall bars={profitBars(b)} unit="tỷ" label={`Thác nước lợi nhuận ${symbol} ${ql(b.quarter)}`} />
          {profitNotes(b).length > 0 && <ul data-testid="profit-notes">{profitNotes(b).map((n) => <li key={n}>{n}</li>)}</ul>}
        </>}
        <p className="caption">Từ báo cáo kết quả kinh doanh đã công bố (VNDirect). Doanh thu = phần doanh thu tăng thêm × biên gộp cùng kỳ; Biên gộp = doanh thu kỳ này
          × chênh lệch biên. Chi phí và thuế tăng là kéo xuống. Phần không khớp dòng nào (doanh nghiệp trình bày khác) hiện riêng ở dòng Khác, không chia vào dòng nào.</p>
      </>}
    </section>
  );
}
