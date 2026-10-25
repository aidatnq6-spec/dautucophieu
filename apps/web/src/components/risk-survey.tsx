"use client";
import { useEffect, useState } from "react";
import { ClipboardCheck } from "lucide-react";
import { ApiError, api, requestId, type ApiFailure } from "../lib/api";
import { FormErrors } from "./form-errors";

type Question = { id: number; text: string; options: { key: string; points: number; text: string }[] };
type Questionnaire = { version: string; notice: string; notes: Record<string, string>; groups: { group: string; label: string }[]; questions: Question[] };
export type RiskAssessment = { total: number; group: string; flags: { code: string; questions: number[] }[]; unresolved_conflicts: string[];
  blocks_capital_increase: boolean; ready_for_allocation: boolean; questionnaire_version: string };

export const FLAG_LABEL: Record<string, string> = {
  capacity_shortfall: "Khả năng tài chính chưa đủ: chưa đề xuất tăng vốn cổ phiếu",
  emergency_review: "Cần rà soát quỹ dự phòng",
  near_term_money: "Có khoản tiền cần sớm: cần tách riêng",
  answer_conflict_loss_tolerance: "Câu 10 và câu 11/13 mâu thuẫn về mức chịu lỗ",
  profile_conflict_emergency: "Hồ sơ cho thấy quỹ dự phòng chưa đủ thanh khoản, khác câu trả lời câu 6",
};
export const GROUP_LABEL: Record<string, string> = { very_safe: "Rất an toàn", cautious: "Thận trọng", moderately_cautious: "Thận trọng vừa phải",
  balanced: "Cân bằng", growth: "Tăng trưởng", strong_growth: "Tăng trưởng mạnh" };

export function RiskSurvey({ version, onSaved }: { version: number; onSaved: (result: RiskAssessment) => void }) {
  const [form, setForm] = useState<Questionnaire | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const [result, setResult] = useState<RiskAssessment | null>(null);
  const [failure, setFailure] = useState<ApiFailure | null>(null);
  const [local, setLocal] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(version);

  useEffect(() => { api<Questionnaire>("risk/questionnaire").then(setForm).catch((e) => e instanceof ApiError && setFailure(e.failure)); }, []);

  async function submit() {
    const missing = form?.questions.filter((q) => !answers[q.id]).map((q) => `Câu ${q.id} chưa trả lời`) ?? [];
    setLocal(missing);
    setFailure(null);
    if (missing.length) return;
    setBusy(true);
    try {
      const body = { answers: Object.entries(answers).map(([q, a]) => ({ question: Number(q), answer: a })), confirmed_conflicts: confirmed,
        expected_version: saved, request_id: requestId() };
      const res = await api<{ version: number; assessment: RiskAssessment }>("risk", { method: "PUT", body });
      setSaved(res.version);
      setResult(res.assessment);
      onSaved(res.assessment);
    } catch (e) { if (e instanceof ApiError) setFailure(e.failure); }
    finally { setBusy(false); }
  }

  if (!form) return <p className="muted">Đang tải bộ câu hỏi…</p>;
  return (
    <form onSubmit={(e) => { e.preventDefault(); void submit(); }} aria-label="Khảo sát rủi ro">
      <p className="notice">{form.notice} Phiên bản: {form.version}.</p>
      <FormErrors failure={failure} local={local} />
      {form.questions.map((q) => (
        <fieldset key={q.id}>
          <legend>Câu {q.id}. {q.text}</legend>
          {q.options.map((o) => (
            <label key={o.key} className="choice">
              <input type="radio" name={`q${q.id}`} value={o.key} checked={answers[q.id] === o.key}
                onChange={() => { setAnswers((a) => ({ ...a, [q.id]: o.key })); setResult(null); }} />
              <span><strong>{o.key}.</strong> {o.text}</span>
            </label>
          ))}
          {form.notes[String(q.id)] && <p className="caption">{form.notes[String(q.id)]}</p>}
        </fieldset>
      ))}
      {result && (
        <section className="surface" aria-live="polite">
          <div className="row"><h2>Kết quả khảo sát tổng hợp</h2><span className="pill">{GROUP_LABEL[result.group] ?? result.group} · {result.total} điểm</span></div>
          {result.flags.length === 0 && <p>Không có cờ cần rà soát.</p>}
          <ul>{result.flags.map((f) => <li key={f.code}>{FLAG_LABEL[f.code] ?? f.code}</li>)}</ul>
          {result.unresolved_conflicts.map((c) => (
            <label key={c} className="choice"><input type="checkbox" checked={confirmed.includes(c)}
              onChange={(e) => setConfirmed((list) => e.target.checked ? [...list, c] : list.filter((x) => x !== c))} />
              Tôi đã xem lại và xác nhận: {FLAG_LABEL[c] ?? c}</label>
          ))}
        </section>
      )}
      <div className="actions"><button type="submit" className="btn primary" disabled={busy}><ClipboardCheck size={16} aria-hidden="true" />
        {result?.unresolved_conflicts.length ? "Lưu xác nhận" : "Lưu câu trả lời"}</button></div>
    </form>
  );
}
