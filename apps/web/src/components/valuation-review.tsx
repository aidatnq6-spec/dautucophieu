"use client";
import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { ApiError, api, requestId, type ApiFailure } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";
import { FormErrors } from "./form-errors";

export type ValuationView = { version: number; last_approved_version: number | null;
  assumptions: { model: string; status: string; approved_at: string | null; required_margin: string | null; sources: string[];
    scenarios: Record<string, { discount_rate: string; terminal_growth: string; cash_flows: string[] }> };
  valuation: { status: string; buy_zone_active: boolean; reason: string | null; scenarios: Record<string, { per_share: string; equity_value: string }> } };
const MODEL: Record<string, string> = { fcff_dcf: "DCF dòng tiền doanh nghiệp", fcfe_dcf: "DCF dòng tiền vốn chủ", ddm: "Chiết khấu cổ tức" };
const SCEN: [string, string][] = [["down", "Bất lợi"], ["base", "Cơ sở"], ["up", "Thuận lợi"]];

export function ValuationReview({ entityId, view, onChanged }: { entityId: string; view: ValuationView; onChanged: () => void }) {
  const [failure, setFailure] = useState<ApiFailure | null>(null);
  const a = view.assumptions, v = view.valuation;
  async function approve() {
    setFailure(null);
    try { await api(`valuation/${entityId}/approve`, { method: "POST", body: { draft_version: view.version, request_id: requestId() } }); onChanged(); }
    catch (e) { if (e instanceof ApiError) setFailure(e.failure); }
  }
  return (
    <section className="surface" data-testid="valuation">
      <div className="row"><h2>Định giá · {MODEL[a.model] ?? a.model}</h2>
        <span className={`pill ${v.buy_zone_active ? "good" : "warn"}`}>{a.status === "approved" ? `Đã duyệt · phiên bản ${view.version}` : "Bản nháp — chưa kích hoạt vùng giá"}</span></div>
      <FormErrors failure={failure} />
      {v.status === "unavailable" ? <p className="notice">Chưa đủ đầu vào cho mô hình ({v.reason}).</p> : (
        <div className="tablewrap"><table aria-label="Ba kịch bản định giá">
          <thead><tr><th>Kịch bản</th><th className="num">Chiết khấu</th><th className="num">Tăng trưởng dài hạn</th><th className="num">Giá trị / cổ phiếu</th></tr></thead>
          <tbody>{SCEN.map(([k, l]) => (
            <tr key={k}><td>{l}</td><td className="num">{formatRatio(a.scenarios[k]?.discount_rate)}</td><td className="num">{formatRatio(a.scenarios[k]?.terminal_growth)}</td>
              <td className="num">{formatVnd(v.scenarios[k]?.per_share ?? null)}</td></tr>))}</tbody>
        </table></div>
      )}
      <p className="caption">Biên an toàn yêu cầu: {a.required_margin ? formatRatio(a.required_margin) : "chưa đặt"} · Nguồn giả định: {a.sources.join(", ") || "chưa có"}</p>
      {a.status === "draft" && <div className="actions"><button className="btn primary" onClick={() => void approve()}><ShieldCheck size={16} aria-hidden="true" />Duyệt giả định</button></div>}
      {a.status === "draft" && view.last_approved_version && <p className="caption">Phiên bản đã duyệt gần nhất: {view.last_approved_version}</p>}
    </section>
  );
}
