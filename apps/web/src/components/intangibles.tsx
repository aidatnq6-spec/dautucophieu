"use client";
import { useEffect, useState } from "react";
import { BookPlus, Pencil, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, hanoiDate, parseMoneyInput } from "../lib/format";

type Entry = { id: string; on: string; kind: string; title: string; amount: string; skill: string };
export type IntangiblesView = { version: number; target_rate: string; entries: Entry[];
  year: { year: number; spent: string; target: string | null; progress: string | null } };

const KIND: Record<string, string> = { course: "Khóa học", certificate: "Chứng chỉ", book: "Sách", other: "Khác" };
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
/** Typed amount (grouped digits, optional leading minus) to whole đồng, or null. */
function toAmount(raw: string): string | null {
  const a = raw.trim().startsWith("-") ? "-" + (parseMoneyInput(raw.replace("-", "")) ?? "") : parseMoneyInput(raw);
  return !a || a === "-" || a.includes(".") ? null : a;
}
const typedAmount = (raw: string) => (raw.trim().startsWith("-") ? "-" : "") + groupDigitsInput(raw);

/** Money put into oneself, the base of the asset pyramid: a log against a share of yearly income, each line editable. Not counted as financial assets. */
export function Intangibles({ onChanged }: { onChanged: () => void }) {
  const [view, setView] = useState<IntangiblesView | null>(null);
  const [kind, setKind] = useState("course");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [skill, setSkill] = useState("");
  const [on, setOn] = useState(hanoiDate());
  const [rate, setRate] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [draft, setDraft] = useState<Entry | null>(null);
  useEffect(() => {
    api<IntangiblesView>("intangibles").then((v) => { setView(v); setRate(v.target_rate.replace(".", ",")); },
      (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  async function add() {
    const a = toAmount(amount);
    if (!title.trim() || !a) { setMessage("Nhập nội dung và số tiền (số âm để điều chỉnh)."); return; }
    try {
      setView(await api<IntangiblesView>("intangibles/entries", { method: "POST",
        body: { on, kind, title: title.trim(), amount: a, skill: skill.trim(), request_id: requestId().slice(0, 64) } }));
      setTitle(""); setAmount(""); setSkill(""); setMessage(null); onChanged();
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  async function saveEdit() {
    if (!draft) return;
    const a = toAmount(draft.amount);
    if (!draft.title.trim() || !a) { setMessage("Nhập nội dung và số tiền (số âm để điều chỉnh)."); return; }
    try {
      setView(await api<IntangiblesView>(`intangibles/entries/${encodeURIComponent(draft.id)}`, { method: "PUT",
        body: { on: draft.on, kind: draft.kind, title: draft.title.trim(), amount: a, skill: draft.skill.trim(), request_id: requestId() } }));
      setDraft(null); setMessage(null); onChanged();
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  async function remove(e: Entry) {
    if (!window.confirm(`Xóa dòng "${e.title}" (${formatVnd(e.amount)})?`)) return;
    try {
      setView(await api<IntangiblesView>(`intangibles/entries/${encodeURIComponent(e.id)}/delete`, { method: "POST", body: { request_id: requestId() } }));
      if (draft?.id === e.id) setDraft(null);
      setMessage(null); onChanged();
    } catch (err) { setMessage(err instanceof ApiError ? err.failure.message : "Lỗi xóa."); }
  }
  async function saveRate() {
    const r = parseMoneyInput(rate);
    if (r === null) { setMessage("Nhập tỷ lệ mục tiêu, ví dụ 10."); return; }
    try {
      setView(await api<IntangiblesView>("intangibles/target", { method: "PUT", body: { target_rate: r, request_id: requestId() } }));
      setMessage(null); onChanged();
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const y = view?.year;
  return (
    <section className="surface" aria-label="Tài sản vô hình">
      <h2>Tài sản vô hình</h2>
      <p className="caption">Đế của tháp tài sản: tiền đầu tư vào bản thân (khóa học, chứng chỉ, sách) để tăng khả năng tạo thu nhập. Không cộng vào tổng tài sản
        tài chính. Mỗi dòng sửa hoặc xóa được; số âm để ghi khoản hoàn lại.</p>
      {y && <p><strong>Năm {y.year}: đã đầu tư {formatVnd(y.spent)}{y.target ? ` / mục tiêu ${formatVnd(y.target)} (${rate.replace(".", ",") || view!.target_rate}% thu nhập năm)` : ""}</strong>
        {y.progress && <span className="caption"> · đạt {formatRatio(y.progress, 1).replace(",0%", "%")}</span>}
        {!y.target && <span className="caption"> · nhập thu nhập ở Sức khỏe tài chính để có mục tiêu</span>}</p>}
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void add(); }}>
        <label className="field">Ngày<input type="date" value={on} disabled={!view} onChange={(e) => setOn(e.target.value)} /></label>
        <label className="field">Loại<select value={kind} disabled={!view} onChange={(e) => setKind(e.target.value)}>
          {Object.entries(KIND).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label className="field">Nội dung<input value={title} maxLength={200} disabled={!view} onChange={(e) => setTitle(e.target.value)} /></label>
        <label className="field">Số tiền (đ)<input inputMode="numeric" value={amount} disabled={!view}
          onChange={(e) => setAmount((e.target.value.trim().startsWith("-") ? "-" : "") + groupDigitsInput(e.target.value))} /></label>
        <label className="field">Kỹ năng thu được<input value={skill} maxLength={300} disabled={!view} onChange={(e) => setSkill(e.target.value)} /></label>
        <button type="submit" className="btn primary" disabled={!view}><BookPlus size={16} aria-hidden="true" />Thêm vào sổ</button>
      </form>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void saveRate(); }}>
        <label className="field">Mục tiêu (% thu nhập năm)<input inputMode="decimal" value={rate} disabled={!view} onChange={(e) => setRate(e.target.value)} /></label>
        <button type="submit" className="btn" disabled={!view}>Lưu mục tiêu</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {view && view.entries.length > 0 && <table className="fv-table cc-table" aria-label="Sổ tài sản vô hình">
        <thead><tr><th>Ngày</th><th>Loại</th><th>Nội dung</th><th className="num">Số tiền</th><th /></tr></thead>
        <tbody>{view.entries.map((e) => draft?.id === e.id ? <tr key={e.id} aria-label={`Sửa dòng ${e.title}`}>
          <td data-label="Ngày"><input type="date" aria-label="Ngày" value={draft.on} onChange={(v) => setDraft({ ...draft, on: v.target.value })} /></td>
          <td data-label="Loại"><select aria-label="Loại" value={draft.kind} onChange={(v) => setDraft({ ...draft, kind: v.target.value })}>
            {Object.entries(KIND).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
          <td data-label="Nội dung"><input aria-label="Nội dung" value={draft.title} maxLength={200} onChange={(v) => setDraft({ ...draft, title: v.target.value })} />
            <input aria-label="Kỹ năng thu được" value={draft.skill} maxLength={300} placeholder="Kỹ năng thu được"
              onChange={(v) => setDraft({ ...draft, skill: v.target.value })} /></td>
          <td data-label="Số tiền" className="num"><input inputMode="numeric" aria-label="Số tiền (đ)" value={draft.amount}
            onChange={(v) => setDraft({ ...draft, amount: typedAmount(v.target.value) })} /></td>
          <td className="actions"><button type="button" className="btn primary" onClick={() => void saveEdit()}>Lưu</button>
            <button type="button" className="btn" onClick={() => { setDraft(null); setMessage(null); }}>Hủy</button></td></tr>
          : <tr key={e.id}>
          <td data-label="Ngày">{day(e.on)}</td><td data-label="Loại">{KIND[e.kind] ?? e.kind}</td>
          <td data-label="Nội dung">{e.title}{e.skill && <div className="caption">{e.skill}</div>}</td>
          <td data-label="Số tiền" className={`num ${e.amount.startsWith("-") ? "negative" : ""}`}>{formatVnd(e.amount)}</td>
          <td className="actions"><button type="button" className="btn" aria-label={`Sửa ${e.title}`}
            onClick={() => { setDraft({ ...e, amount: typedAmount(e.amount) }); setMessage(null); }}><Pencil size={14} aria-hidden="true" />Sửa</button>
            <button type="button" className="btn" aria-label={`Xóa ${e.title}`} onClick={() => void remove(e)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td></tr>)}</tbody>
      </table>}
    </section>
  );
}
