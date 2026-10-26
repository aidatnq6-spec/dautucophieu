"use client";
import { useCallback, useEffect, useState } from "react";
import { Check, RotateCcw } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio } from "../lib/format";
import { FLAG_LABEL, GROUP_LABEL, type RiskAssessment } from "./risk-survey";

type RiskView = { version: number; assessment: RiskAssessment; assessed_at: string; override_version: number;
  effective: { group: string; manual: boolean; score_range: [number, number]; equity_ratio: string } };

const GROUPS = ["very_safe", "cautious", "moderately_cautious", "balanced", "growth", "strong_growth"];
const pct = (r: string) => formatRatio(r, 1).replace(",0%", "%");

/** Survey result, plus a group chosen by hand that replaces it everywhere until the owner goes back to the survey. */
export function RiskSection({ onChanged }: { onChanged: () => void }) {
  const [r, setR] = useState<RiskView | null | undefined>(undefined);
  const [choice, setChoice] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(() => {
    api<RiskView>("risk").then((v) => { setR(v); setChoice(v.effective.group); }).catch((e) => {
      if (e instanceof ApiError && e.failure.status === 404) setR(null);
      else setMessage(e instanceof ApiError ? e.failure.message : "Không tải được dữ liệu.");
    });
  }, []);
  useEffect(load, [load]);
  async function apply(group: string | null) {
    if (!r) return;
    try {
      await api("risk/override", { method: "PUT", body: { group, expected_version: r.override_version, request_id: requestId() } });
      setMessage(null); load(); onChanged();
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  return (
    <section className="surface" aria-label="Khảo sát rủi ro">
      <h2>Khảo sát rủi ro</h2>
      {r === undefined && !message && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {r === null && <p className="notice">Chưa có kết quả khảo sát.</p>}
      {r && (<>
        <p><span className="pill" data-testid="risk-effective">{GROUP_LABEL[r.effective.group]} · {r.effective.manual
          ? `${r.effective.score_range[0]}–${r.effective.score_range[1]}` : r.assessment.total} điểm · cổ phiếu {pct(r.effective.equity_ratio)}</span>{r.effective.manual && <> <span className="pill warn">Tự chọn</span></>}</p>
        {r.effective.manual
          ? <p className="caption">Kết quả khảo sát: {GROUP_LABEL[r.assessment.group]} · {r.assessment.total} điểm. Nhóm tự chọn đang thay kết quả này ở mọi nơi
            (vốn dành cho cổ phiếu, giới hạn mua trong khuyến nghị).</p>
          : <p className="caption">Theo khảo sát; nhóm này ứng với {r.effective.score_range[0]}–{r.effective.score_range[1]} điểm.</p>}
        <p className="caption">Khảo sát tổng hợp bản nháp, chưa được kiểm định · {r.assessment.questionnaire_version}</p>
        <ul>{r.assessment.flags.map((f) => <li key={f.code}>{FLAG_LABEL[f.code] ?? f.code}</li>)}</ul>
        <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void apply(choice); }}>
          <label className="field">Chọn nhóm thủ công<select value={choice} onChange={(e) => setChoice(e.target.value)}>
            {GROUPS.map((g) => <option key={g} value={g}>{GROUP_LABEL[g]}</option>)}</select></label>
          <button type="submit" className="btn primary"><Check size={16} aria-hidden="true" />Áp dụng</button>
          {r.effective.manual && <button type="button" className="btn" onClick={() => void apply(null)}>
            <RotateCcw size={16} aria-hidden="true" />Dùng lại kết quả khảo sát</button>}
        </form>
      </>)}
      {message && <p className="errors" role="alert">{message}</p>}
    </section>
  );
}
