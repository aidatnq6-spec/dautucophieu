"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";

export type Stage = "idea" | "research" | "waiting" | "holding" | "sold";
export type Card = { id: string; symbol: string; stage: Stage; note: string; lesson: string; moved_on: string; days: number; hints: string[] };
type Board = { version: number; columns: { stage: Stage; label: string; cards: Card[] }[]; held_without_card: string[] };
const ORDER: Stage[] = ["idea", "research", "waiting", "holding", "sold"];

/** The cards to send after moving one card a column left (−1) or right (+1); null at either end. */
export function moveCard(cards: Card[], id: string, step: -1 | 1): Card[] | null {
  const card = cards.find((c) => c.id === id);
  if (!card) return null;
  const next = ORDER.indexOf(card.stage) + step;
  if (next < 0 || next >= ORDER.length) return null;
  return cards.map((c) => (c.id === id ? { ...c, stage: ORDER[next] } : c));
}

const toSend = (cards: Card[]) => cards.map(({ id, symbol, stage, note, lesson }) => ({ id, symbol, stage, note, lesson }));

export function IdeaBoard() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [symbol, setSymbol] = useState("");
  const [editing, setEditing] = useState<{ id: string; note: string; lesson: string } | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api<Board>("journal/board").then(setBoard, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const cards = board?.columns.flatMap((c) => c.cards) ?? [];
  const save = async (next: Card[] | { id: string; symbol: string; stage: Stage; note: string; lesson: string }[]) => {
    if (!board) return;
    setBusy(true); setError(null);
    try {
      setBoard(await api<Board>("journal/board", { method: "PUT", body: { cards: next.map((c) => ({ id: c.id, symbol: c.symbol, stage: c.stage, note: c.note,
        lesson: c.lesson })), expected_version: board.version, request_id: requestId() } }));
      setEditing(null);
    } catch (e) { setError(e instanceof ApiError ? e.failure.message : "Không lưu được."); }
    setBusy(false);
  };
  const add = (sym: string, stage: Stage = "idea") => {
    const s = sym.trim().toUpperCase();
    if (!/^[A-Z0-9]{3,10}$/.test(s)) { setError("Nhập mã cổ phiếu, ví dụ FPT."); return; }
    void save([...toSend(cards), { id: requestId().slice(0, 32), symbol: s, stage, note: "", lesson: "" }]).then(() => setSymbol(""));
  };
  return (
    <section className="surface" aria-label="Quy trình đầu tư">
      <h2>Quy trình đầu tư</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!board && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {board && <>
        <form className="ib-add" onSubmit={(e) => { e.preventDefault(); add(symbol); }}>
          <label className="field">Mã mới<input aria-label="Mã mới" value={symbol} maxLength={10} onChange={(e) => setSymbol(e.target.value)} placeholder="FPT" /></label>
          <button type="submit" className="btn" disabled={busy}>Thêm vào Ý tưởng</button>
        </form>
        {board.held_without_card.length > 0 && <p className="caption" data-testid="held-without-card">Đang nắm theo sổ lệnh nhưng chưa có thẻ:{" "}
          {board.held_without_card.map((s) => <button key={s} type="button" className="btn ib-chip" disabled={busy} onClick={() => add(s, "holding")}>+ {s}</button>)}</p>}
        <div className="ib-board">
          {board.columns.map((col) => <div key={col.stage} className="ib-col" role="group" aria-label={col.label}>
            <h3>{col.label} <span className="muted">({col.cards.length})</span></h3>
            {col.cards.map((c) => <article key={c.id} className="ib-card" aria-label={`Thẻ ${c.symbol}`}>
              <div className="ib-top"><Link href={`/research/${c.symbol}`}><strong>{c.symbol}</strong></Link><span className="caption">{c.days} ngày</span></div>
              {editing?.id === c.id ? <>
                <label className="field">Ghi chú<textarea aria-label={`Ghi chú ${c.symbol}`} maxLength={300} value={editing.note}
                  onChange={(e) => setEditing({ ...editing, note: e.target.value })} /></label>
                {c.stage === "sold" && <label className="field">Bài học<textarea aria-label={`Bài học ${c.symbol}`} maxLength={500} value={editing.lesson}
                  onChange={(e) => setEditing({ ...editing, lesson: e.target.value })} /></label>}
                <div className="ib-actions"><button type="button" className="btn" disabled={busy}
                  onClick={() => void save(cards.map((x) => (x.id === c.id ? { ...x, note: editing.note, lesson: editing.lesson } : x)))}>Lưu</button>
                  <button type="button" className="btn" onClick={() => setEditing(null)}>Hủy</button></div>
              </> : <>
                {c.note && <p className="ib-note">{c.note}</p>}
                {c.lesson && <p className="ib-note"><strong>Bài học:</strong> {c.lesson}</p>}
                {c.hints.map((h) => <p key={h} className="ib-hint">{h}</p>)}
                <div className="ib-actions">
                  <button type="button" className="btn" aria-label={`Chuyển ${c.symbol} sang trái`} disabled={busy || c.stage === "idea"}
                    onClick={() => { const n = moveCard(cards, c.id, -1); if (n) void save(n); }}>←</button>
                  <button type="button" className="btn" aria-label={`Chuyển ${c.symbol} sang phải`} disabled={busy || c.stage === "sold"}
                    onClick={() => { const n = moveCard(cards, c.id, 1); if (n) void save(n); }}>→</button>
                  <button type="button" className="btn" aria-label={`Sửa ${c.symbol}`} disabled={busy}
                    onClick={() => setEditing({ id: c.id, note: c.note, lesson: c.lesson })}>Sửa</button>
                  <button type="button" className="btn" aria-label={`Xóa ${c.symbol}`} disabled={busy}
                    onClick={() => { if (window.confirm(`Xóa thẻ ${c.symbol}?`)) void save(cards.filter((x) => x.id !== c.id)); }}>Xóa</button>
                </div>
              </>}
            </article>)}
          </div>)}
        </div>
        <p className="caption">Mỗi mã một thẻ. Số ngày tính từ khi thẻ vào cột hiện tại. Phần mềm so thẻ với sổ lệnh và luận điểm để nhắc chỗ lệch, không tự chuyển thẻ
          và không đặt lệnh.</p>
      </>}
    </section>
  );
}
