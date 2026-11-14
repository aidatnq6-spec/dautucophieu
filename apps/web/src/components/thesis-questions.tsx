"use client";
import { useState } from "react";
import { requestId } from "../lib/api";

export type QKey = "business" | "strategy" | "industry" | "valuation" | "monitoring" | "timing";
type Status = "good" | "watch" | "bad" | null;
export type Gap = { id: string; text: string; ref: string; done: boolean };
export type Question = { status: Status; summary: string; points: string[]; gaps: Gap[] };
export type Catalyst = { id: string; when: string; on: string | null; sign: "+" | "-" | "?"; text: string; source: string; done: boolean };
type Parts = { questions: Record<string, Question>; catalysts: Catalyst[]; stage: "draft" | "reviewed" };

export const QUESTIONS: [QKey, string][] = [["business", "Doanh nghiệp kiếm tiền thế nào"], ["strategy", "Chiến lược và động lực tăng trưởng"],
  ["industry", "Ngành và chu kỳ ngành"], ["valuation", "Định giá"], ["monitoring", "Theo dõi, cơ hội, rủi ro"], ["timing", "Thời điểm"]];
const STATUS: Record<"good" | "watch" | "bad", [string, string]> = { good: ["Tốt", "good"], watch: ["Theo dõi", "warn"], bad: ["Xấu", "bad"] };
const SIGN: Record<Catalyst["sign"], string> = { "+": "+", "-": "−", "?": "?" };
const EMPTY_Q: Question = { status: null, summary: "", points: [], gaps: [] };

/** "Độ đủ dữ liệu": open gaps over all gaps, across the six questions. */
export function gapText(questions: Record<string, Question>): string {
  const gaps = Object.values(questions).flatMap((q) => q.gaps);
  return gaps.length ? `${gaps.filter((g) => !g.done).length}/${gaps.length} việc mở` : "chưa ghi chỗ trống";
}

export function ThesisQuestions<M extends Parts>({ model, save, busy }: { model: M; save: (m: M) => Promise<void>; busy: boolean }) {
  const [editing, setEditing] = useState<{ key: QKey; q: Question; points: string } | null>(null);
  const [gapDraft, setGapDraft] = useState<Record<string, { text: string; ref: string }>>({});
  const q = (k: QKey) => model.questions[k] ?? EMPTY_Q;
  const put = (k: QKey, next: Question) => save({ ...model, questions: { ...model.questions, [k]: next } });
  return (
    <>
      <div className="row"><h3>Sáu câu hỏi của luận điểm</h3>
        <span><span className={`pill ${model.stage === "reviewed" ? "good" : "warn"}`}>{model.stage === "reviewed" ? "Đã nghiệm thu" : "Nháp"}</span>{" "}
          <span className="caption" data-testid="tq-gaps">Độ đủ dữ liệu: {gapText(model.questions)}</span>{" "}
          <button type="button" className="btn" disabled={busy} onClick={() => void save({ ...model, stage: model.stage === "reviewed" ? "draft" : "reviewed" })}>
            {model.stage === "reviewed" ? "Chuyển về nháp" : "Đánh dấu đã nghiệm thu"}</button></span></div>
      <div className="tq-grid">{QUESTIONS.map(([key, title], n) => { const cur = q(key);
        return <article key={key} className="tq-card" aria-label={`Câu ${n + 1}: ${title}`}>
          <div className="row"><strong>{n + 1} · {title}</strong>{cur.status && <span className={`pill ${STATUS[cur.status][1]}`}>{STATUS[cur.status][0]}</span>}</div>
          {editing?.key === key ? <>
            <label className="field">Trạng thái<select aria-label={`Trạng thái câu ${n + 1}`} value={editing.q.status ?? ""}
              onChange={(e) => setEditing({ ...editing, q: { ...editing.q, status: (e.target.value || null) as Status } })}>
              <option value="">Chưa đánh giá</option><option value="good">Tốt</option><option value="watch">Theo dõi</option><option value="bad">Xấu</option></select></label>
            <label className="field">Trả lời ngắn<input aria-label={`Trả lời câu ${n + 1}`} maxLength={300} value={editing.q.summary}
              onChange={(e) => setEditing({ ...editing, q: { ...editing.q, summary: e.target.value } })} /></label>
            <label className="field">Ý chính (mỗi dòng một ý)<textarea aria-label={`Ý chính câu ${n + 1}`} rows={4} value={editing.points}
              onChange={(e) => setEditing({ ...editing, points: e.target.value })} /></label>
            <div className="ib-actions"><button type="button" className="btn" disabled={busy}
              onClick={() => void put(key, { ...editing.q, points: editing.points.split("\n").map((p) => p.trim()).filter(Boolean) }).then(() => setEditing(null))}>Lưu</button>
              <button type="button" className="btn" onClick={() => setEditing(null)}>Hủy</button></div>
          </> : <>
            {cur.summary ? <p className="tq-summary">{cur.summary}</p> : <p className="muted">Chưa trả lời.</p>}
            {cur.points.length > 0 && <ul className="tq-points">{cur.points.map((p, i) => <li key={i}>{p}</li>)}</ul>}
            <button type="button" className="btn" aria-label={`Sửa câu ${n + 1}`} onClick={() => setEditing({ key, q: cur, points: cur.points.join("\n") })}>Sửa</button>
          </>}
          <div className="tq-gaps">
            {cur.gaps.map((g) => <label key={g.id} className={g.done ? "tq-gap done" : "tq-gap"}>
              <input type="checkbox" checked={g.done} disabled={busy} aria-label={`Xong: ${g.text}`}
                onChange={() => void put(key, { ...cur, gaps: cur.gaps.map((x) => (x.id === g.id ? { ...x, done: !x.done } : x)) })} />
              <span className="pill warn">GAP</span> {g.text}{g.ref && <span className="caption"> ({g.ref})</span>}
              <button type="button" className="btn tq-x" aria-label={`Xóa chỗ trống ${g.text}`} disabled={busy}
                onClick={() => void put(key, { ...cur, gaps: cur.gaps.filter((x) => x.id !== g.id) })}>×</button></label>)}
            <div className="ib-actions">
              <input aria-label={`Chỗ trống mới câu ${n + 1}`} placeholder="Còn thiếu gì?" maxLength={200} value={gapDraft[key]?.text ?? ""}
                onChange={(e) => setGapDraft({ ...gapDraft, [key]: { text: e.target.value, ref: gapDraft[key]?.ref ?? "" } })} />
              <input aria-label={`Mã chỗ trống câu ${n + 1}`} placeholder="PHP-01" maxLength={20} className="tq-ref" value={gapDraft[key]?.ref ?? ""}
                onChange={(e) => setGapDraft({ ...gapDraft, [key]: { text: gapDraft[key]?.text ?? "", ref: e.target.value } })} />
              <button type="button" className="btn" disabled={busy || !gapDraft[key]?.text?.trim()} onClick={() => void put(key, { ...cur, gaps: [...cur.gaps,
                { id: requestId().slice(0, 24), text: gapDraft[key].text, ref: gapDraft[key].ref, done: false }] }).then(() => setGapDraft({ ...gapDraft, [key]: { text: "", ref: "" } }))}>
                Thêm chỗ trống</button></div>
          </div>
        </article>; })}</div>
    </>
  );
}

const BLANK: Omit<Catalyst, "id"> = { when: "", on: null, sign: "+", text: "", source: "", done: false };

export function ThesisCatalysts<M extends Parts>({ model, save, busy, due }: { model: M; save: (m: M) => Promise<void>; busy: boolean; due: string[] }) {
  const [draft, setDraft] = useState<Omit<Catalyst, "id">>(BLANK);
  const list = model.catalysts;
  return (
    <>
      <h3>Mốc và chất xúc tác</h3>
      {list.length > 0 && <table className="fv-table" aria-label="Mốc và chất xúc tác">
        <thead><tr><th>Thời điểm</th><th>Dấu</th><th>Nội dung</th><th>Nguồn</th><th /></tr></thead>
        <tbody>{list.map((c) => <tr key={c.id} className={c.done ? "tq-done" : undefined}>
          <td data-label="Thời điểm">{c.when || "chưa có mốc"}{c.on && <div className="caption">nhắc {c.on.split("-").reverse().join("/")}</div>}
            {due.includes(c.id) && <span className="pill warn">đã đến mốc</span>}</td>
          <td data-label="Dấu"><span className={c.sign === "+" ? "fd-up" : c.sign === "-" ? "fd-down" : undefined}><strong>{SIGN[c.sign]}</strong></span></td>
          <td data-label="Nội dung">{c.text}</td><td data-label="Nguồn">{c.source || "—"}</td>
          <td data-label="Thao tác"><div className="ib-actions">
            <button type="button" className="btn" disabled={busy} onClick={() => void save({ ...model, catalysts: list.map((x) => (x.id === c.id ? { ...x, done: !x.done } : x)) })}>
              {c.done ? "Mở lại" : "Đã xảy ra"}</button>
            <button type="button" className="btn" aria-label={`Xóa mốc ${c.text}`} disabled={busy}
              onClick={() => { if (window.confirm("Xóa mốc này?")) void save({ ...model, catalysts: list.filter((x) => x.id !== c.id) }); }}>Xóa</button></div></td></tr>)}</tbody>
      </table>}
      <form className="formgrid" aria-label="Thêm mốc" onSubmit={(e) => { e.preventDefault();
        void save({ ...model, catalysts: [...list, { ...draft, id: requestId().slice(0, 24) }] }).then(() => setDraft(BLANK)); }}>
        <label className="field">Thời điểm<input aria-label="Thời điểm mốc" placeholder="Q4/2026" maxLength={20} value={draft.when} onChange={(e) => setDraft({ ...draft, when: e.target.value })} /></label>
        <label className="field">Ngày nhắc<input aria-label="Ngày nhắc mốc" type="date" value={draft.on ?? ""} onChange={(e) => setDraft({ ...draft, on: e.target.value || null })} /></label>
        <label className="field">Dấu<select aria-label="Dấu mốc" value={draft.sign} onChange={(e) => setDraft({ ...draft, sign: e.target.value as Catalyst["sign"] })}>
          <option value="+">+ thuận lợi</option><option value="-">− bất lợi</option><option value="?">? chưa rõ</option></select></label>
        <label className="field">Nội dung<input aria-label="Nội dung mốc" maxLength={200} value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })} /></label>
        <label className="field">Nguồn<input aria-label="Nguồn mốc" maxLength={120} value={draft.source} onChange={(e) => setDraft({ ...draft, source: e.target.value })} /></label>
        <button type="submit" className="btn" disabled={busy || !draft.text.trim()}>Thêm mốc</button>
      </form>
    </>
  );
}
