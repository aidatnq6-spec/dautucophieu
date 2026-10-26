"use client";
import { useCallback, useEffect, useState } from "react";
import { NotebookPen, Plus } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

export const EMOTIONS: [string, string][] = [["calm", "Bình tĩnh"], ["excited", "Hào hứng"], ["fomo", "Sợ bỏ lỡ (FOMO)"], ["anxious", "Lo lắng"],
  ["panic", "Hoảng sợ"], ["regret", "Tiếc nuối"]];
const EMOTION = Object.fromEntries(EMOTIONS);
const KIND: Record<string, string> = { buy: "Mua", sell: "Bán", hold: "Đang giữ" };
const VERDICT: Record<string, string> = { cheap: "Rẻ", fair: "Hợp lý", expensive: "Đắt" };

type Context = { price: string | null; pe: string | null; verdict: string | null; macd_d1: string | null; rsi_d1: number | null; vnindex: string | null };
type Entry = { entry_id: string; symbol: string; kind: string; created_on: string; reason: string; emotion: string | null; emotion_note: string;
  context: Partial<Context>; notes: { on: string; text: string }[]; current_price: string | null; change: string | null };
type Data = { threshold: string; held: string[]; entries: Entry[] };

const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const failure = (e: unknown, fallback: string) => (e instanceof ApiError ? e.failure.message : fallback);

/** Save a journal entry; the server captures the market context at this moment. */
export function saveJournal(body: { symbol: string; kind: string; reason: string; emotion: string | null; emotion_note: string; ledger_event_id?: string }) {
  return api<Entry>("journal", { method: "POST", body: { ...body, request_id: requestId().slice(0, 64) } });
}

export function EmotionFields({ emotion, note, onEmotion, onNote }: { emotion: string; note: string; onEmotion: (v: string) => void; onNote: (v: string) => void }) {
  return (<>
    <label className="field">Cảm xúc lúc đó<select value={emotion} onChange={(e) => onEmotion(e.target.value)}>
      <option value="">Không ghi</option>{EMOTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
    <label className="field">Ghi chú cảm xúc<input value={note} maxLength={500} onChange={(e) => onNote(e.target.value)} placeholder="ngắn gọn" /></label>
  </>);
}

function Change({ value }: { value: string | null }) {
  if (value === null) return <span className="muted">—</span>;
  const negative = value.startsWith("-");
  const zero = !/[1-9]/.test(value);
  return <span className={zero ? "" : negative ? "negative" : "positive"}>{negative || zero ? "" : "+"}{formatRatio(value, 1)}</span>;
}

function EntryCard({ e, onChanged }: { e: Entry; onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const c = e.context;
  async function addNote() {
    if (!note.trim()) return;
    try {
      await api(`journal/${e.entry_id}/notes`, { method: "POST", body: { text: note.trim(), request_id: requestId().slice(0, 64) } });
      setNote(""); setMessage(null); onChanged();
    } catch (err) { setMessage(failure(err, "Lỗi lưu ghi chú.")); }
  }
  return (
    <article className="surface jr-entry" aria-label={`${e.symbol} ${KIND[e.kind]} ${day(e.created_on)}`}>
      <header className="jr-head">
        <strong>{e.symbol}</strong> <span className={`pill${e.kind === "buy" ? " good" : e.kind === "sell" ? " bad" : ""}`}>{KIND[e.kind] ?? e.kind}</span>
        <span className="muted">{day(e.created_on)}</span>
        <span className="jr-move">Giá lúc ghi {formatVnd(c.price ?? null)} → nay {formatVnd(e.current_price)} (<Change value={e.change} />)</span>
      </header>
      <p className="jr-reason">{e.reason || <span className="muted">Không ghi lý do.</span>}</p>
      {e.emotion && <p className="caption">Cảm xúc lúc đó: <strong>{EMOTION[e.emotion]}</strong>{e.emotion_note && ` — ${e.emotion_note}`}</p>}
      <button type="button" className="btn" aria-expanded={open} onClick={() => setOpen(!open)}>Bối cảnh lúc ghi</button>
      {open && <ul className="jr-context" aria-label="Bối cảnh lúc ghi">
        <li>Giá: {formatVnd(c.price ?? null)}</li>
        <li>P/E: {c.pe ? formatDecimal(c.pe, 1) : "—"}</li>
        <li>Định giá: {c.verdict ? VERDICT[c.verdict] ?? c.verdict : "—"}</li>
        <li>MACD D1: {c.macd_d1 ?? "—"}</li>
        <li>RSI D1: {c.rsi_d1 ?? "—"}</li>
        <li>VN-Index: {c.vnindex ? formatDecimal(c.vnindex, 2) : "—"}</li>
      </ul>}
      {e.notes.length > 0 && <ul className="jr-notes" aria-label="Ghi chú thêm">
        {e.notes.map((n, i) => <li key={i}><span className="muted">{day(n.on)}</span> {n.text}</li>)}</ul>}
      <form className="jr-addnote" onSubmit={(ev) => { ev.preventDefault(); void addNote(); }}>
        <input aria-label="Thêm ghi chú" value={note} maxLength={2000} onChange={(ev) => setNote(ev.target.value)} placeholder="Suy nghĩ thêm (không sửa nội dung cũ)" />
        <button type="submit" className="btn"><Plus size={16} aria-hidden="true" />Thêm ghi chú</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
    </article>
  );
}

function HoldForm({ held, onSaved }: { held: string[]; onSaved: () => void }) {
  const [symbol, setSymbol] = useState(held[0] ?? "");
  const [reason, setReason] = useState("");
  const [emotion, setEmotion] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function save() {
    if (!symbol || !reason.trim()) { setMessage("Chọn mã và ghi lý do."); return; }
    setBusy(true);
    try {
      await saveJournal({ symbol, kind: "hold", reason: reason.trim(), emotion: emotion || null, emotion_note: note.trim() });
      setReason(""); setEmotion(""); setNote(""); setMessage(null); onSaved();
    } catch (e) { setMessage(failure(e, "Lỗi lưu.")); } finally { setBusy(false); }
  }
  return (
    <form className="surface" aria-label="Ghi lý do đang giữ" onSubmit={(e) => { e.preventDefault(); void save(); }}>
      <h2>Ghi lý do đang giữ</h2>
      {held.length === 0 ? <p className="muted">Chưa nắm mã nào.</p> : (<>
        <div className="formgrid">
          <label className="field">Mã đang nắm<select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {held.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
          <label className="field">Lý do đang giữ<textarea value={reason} maxLength={4000} onChange={(e) => setReason(e.target.value)} /></label>
          <EmotionFields emotion={emotion} note={note} onEmotion={setEmotion} onNote={setNote} />
        </div>
        <div className="actions"><button type="submit" className="btn primary" disabled={busy}><NotebookPen size={16} aria-hidden="true" />Lưu vào nhật ký</button></div>
      </>)}
      {message && <p className="errors" role="alert">{message}</p>}
    </form>
  );
}

/** Why each decision was made and how it felt, beside where the price is now. Entries are never edited; notes are appended. */
export function JournalView() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { api<Data>("journal").then(setD, (e) => setError(failure(e, "Lỗi tải."))); }, []);
  useEffect(load, [load]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!d) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  return (
    <>
      <p className="notice">Mỗi mục lưu lý do, cảm xúc và bối cảnh thị trường lúc ghi; không sửa hay xóa, chỉ thêm ghi chú. Khi giá đi thêm
        {" "}{formatRatio(d.threshold, 1).replace(",0%", "%")} so với giá lúc ghi (lên hoặc xuống), ứng dụng nhắc qua Telegram kèm đúng lý do đã ghi. Chỉ để tự xem lại, không phải khuyến nghị.</p>
      <HoldForm held={d.held} onSaved={load} />
      {d.entries.length === 0 ? <p className="muted">Chưa có mục nào. Ghi lý do khi nhập giao dịch mua/bán, hoặc ghi lý do đang giữ ở trên.</p>
        : d.entries.map((e) => <EntryCard key={e.entry_id} e={e} onChanged={load} />)}
    </>
  );
}
