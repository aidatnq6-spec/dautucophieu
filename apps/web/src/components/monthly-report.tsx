"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { formatRatio, hanoiDate } from "../lib/format";
import { AssetMapView, MonthBridgeView } from "./asset-views";
import { GoalScorecard } from "./goal-scorecard";

type Monthly = { month: string; portfolio: string; vnindex: string };

/** The month's return beside VN-Index's, as one sentence; null when Hiệu quả danh mục has no figure for it. */
export function monthSentence(monthly: Monthly[], month: string): string | null {
  const m = monthly.find((x) => x.month === month);
  if (!m) return null;
  const sign = (v: string) => `${Number(v) > 0 ? "+" : ""}${formatRatio(v, 1)}`;
  const diff = Number(m.portfolio) - Number(m.vnindex);
  return `Danh mục ${sign(m.portfolio)}, VN-Index ${sign(m.vnindex)} trong tháng: ${diff >= 0 ? "hơn" : "kém"} thị trường ${formatRatio(String(Math.abs(diff)), 1)}.`;
}

export function MonthlyReport() {
  const [months, setMonths] = useState<string[] | null>(null);
  const [month, setMonth] = useState<string | null>(null);
  const [monthly, setMonthly] = useState<Monthly[]>([]);
  useEffect(() => {
    api<{ months: string[] }>("month-bridge").then((d) => { setMonths(d.months); setMonth(d.months[0] ?? null); }, () => setMonths([]));
    api<{ monthly: Monthly[] }>("performance").then((p) => setMonthly(p.monthly), () => setMonthly([]));
  }, []);
  const sentence = month ? monthSentence(monthly, month) : null;
  return (
    <div className="mr-page">
      <div className="pagehead mr-head">
        <h1>Tổng kết tháng {month ? `${month.slice(5)}/${month.slice(0, 4)}` : ""}</h1>
        <p className="muted">In ngày {hanoiDate().split("-").reverse().join("/")}. Chỉ để bạn lưu hồ sơ; không phải khuyến nghị.</p>
        <div className="mr-tools">
          {months && months.length > 0 && <label className="field">Tháng<select aria-label="Tháng tổng kết" value={month ?? ""} onChange={(e) => setMonth(e.target.value)}>
            {months.map((m) => <option key={m} value={m}>{m.slice(5)}/{m.slice(0, 4)}</option>)}</select></label>}
          <button type="button" className="btn" onClick={() => window.print()}>In</button>
        </div>
      </div>
      {months && months.length === 0 && <p className="muted">Chưa có giao dịch nào trong sổ lệnh.</p>}
      {sentence && <p className="mr-lead" data-testid="month-sentence">{sentence}</p>}
      {month && <MonthBridgeView key={month} initial={month} />}
      <AssetMapView />
      <GoalScorecard />
    </div>
  );
}
