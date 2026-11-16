"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

export type Spend = { month: string; used_usd: string; monthly_usd: string };
type Answer = { status: "ok" | "unverified" | "no_passages"; answer: string | null; pages: number[]; url: string; cost_usd: string; spend: Spend };

/** Questions from the owner's reading notes on financial statements; none carries a number or a word about the owner. */
export const PRESETS = [
  "Phải thu bên liên quan gồm những đối tượng nào, có bảo đảm và có tính lãi không?",
  "Thuyết minh trả trước cho người bán nêu tên những nhà cung cấp nào?",
  "Có khoản trả trước cho người bán nào được hoàn lại bằng tiền không?",
  "Phải thu khác gồm những khoản gì (đặt cọc, ký quỹ, lãi cho vay phải thu…), của những đối tượng nào?",
  "Phải thu về cho vay gồm những đối tượng nào, lãi suất bao nhiêu, có phải bên liên quan không?",
  "Lãi cho vay phải thu tăng hay giảm so với năm trước, doanh nghiệp đã thu được tiền lãi chưa?",
  "Doanh thu tài chính gồm những khoản gì: lãi tiền gửi, lãi tỷ giá, cổ tức hay lãi bán khoản đầu tư?",
  "Ý kiến kiểm toán có ngoại trừ hay nhấn mạnh vấn đề gì không?",
];

/** A link straight to a page of the document (PDF viewers honour #page=). */
export function pageLink(url: string, page: number): string {
  return `${url.split("#")[0]}#page=${page}`;
}

export function spendText(s: Spend | null | undefined): string {
  if (!s) return "";
  const used = Number(s.used_usd).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  return `Đã dùng ${used} / ${Number(s.monthly_usd).toLocaleString("vi-VN")} USD tháng ${s.month.slice(5)}/${s.month.slice(0, 4)}.`;
}

/** Hỏi AI về tài liệu: one question about one public document of this ticker; nothing of the owner's goes to the model. */
export function DocAsk({ symbol }: { symbol: string }) {
  const [url, setUrl] = useState("");
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [status, setStatus] = useState<{ key_configured: boolean; spend: Spend | null } | null>(null);
  useEffect(() => { api<{ key_configured: boolean; spend: Spend | null }>("ai-docs/status").then(setStatus, () => setStatus(null)); }, []);

  async function ask() {
    setBusy(true); setError(null); setAnswer(null);
    try {
      const a = await api<Answer>(`ai-docs/${symbol}/ask`, { method: "POST", body: { url, question } });
      setAnswer(a);
      setStatus((s) => (s ? { ...s, spend: a.spend } : s));
    } catch (e) { setError(e instanceof ApiError ? e.failure.message : "Không hỏi được."); } finally { setBusy(false); }
  }

  return (
    <section className="surface" aria-label="Hỏi AI về tài liệu">
      <h2>Hỏi AI về tài liệu</h2>
      <p className="caption">Dán link https công khai của một tài liệu của {symbol} (BCTC, thuyết minh, nghị quyết, báo cáo thường niên…) và hỏi một câu.
        Chỉ mã {symbol}, câu hỏi và các đoạn liên quan của tài liệu được gửi cho AI; câu hỏi có số tiền, nói về bạn hay danh mục của bạn, có tên sổ của bạn
        hoặc nhắc mã khác sẽ bị chặn trước khi gửi. {status?.key_configured === false ? "Chưa có key OpenRouter (Cài đặt)." : spendText(status?.spend)}</p>
      <form className="formgrid" aria-label="Câu hỏi về tài liệu" onSubmit={(e) => { e.preventDefault(); void ask(); }}>
        <label className="field">Link tài liệu<input aria-label="Link tài liệu" type="url" maxLength={500} placeholder="https://…/bctc-2025.pdf" value={url}
          onChange={(e) => setUrl(e.target.value)} /></label>
        <div className="doc-presets" role="group" aria-label="Câu hỏi mẫu">{PRESETS.map((p) => (
          <button key={p} type="button" className="btn text" onClick={() => setQuestion(p)}>{p}</button>))}</div>
        <label className="field">Câu hỏi<textarea aria-label="Câu hỏi" maxLength={300} rows={2} placeholder="Thuyết minh nói gì về phải thu bên liên quan?"
          value={question} onChange={(e) => setQuestion(e.target.value)} /></label>
        <div className="actions"><button type="submit" className="btn primary" disabled={busy || !url.trim() || !question.trim()}>{busy ? "Đang hỏi…" : "Hỏi AI"}</button></div>
      </form>
      {error && <p className="errors" role="alert">{error}</p>}
      {answer && <div className="doc-answer" data-testid="doc-answer">
        {answer.status === "ok" && answer.answer ? <>
          <p>{answer.answer}</p>
          <p className="caption">Trang: {answer.pages.map((p, i) => <span key={p}>{i > 0 && ", "}<a href={pageLink(answer.url, p)} target="_blank" rel="noreferrer">{p}</a></span>)}.
            {" "}AI tóm tắt, có thể sai: đối chiếu trang gốc. Chi phí lần hỏi này {answer.cost_usd} USD. {spendText(answer.spend)}</p>
        </> : <p className="muted">{answer.status === "no_passages" ? "Tài liệu không có đoạn nào nói về câu hỏi này; chưa gửi gì cho AI."
          : "AI trả lời không kiểm chứng được với tài liệu (trích số hoặc trang không có trong đoạn đã gửi), nên không hiện câu trả lời."}</p>}
      </div>}
    </section>
  );
}
