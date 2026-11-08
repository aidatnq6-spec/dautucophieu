"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, FileUp, NotebookPen, Plus } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";
import { NO_FILTER, download, filterEntries, spreadsheet, summarize, type Imported, type JournalFilter } from "./journal-tools";

export const EMOTIONS: [string, string][] = [["calm", "Bình tĩnh"], ["excited", "Hào hứng"], ["fomo", "Sợ bỏ lỡ (FOMO)"], ["anxious", "Lo lắng"],
  ["panic", "Hoảng sợ"], ["regret", "Tiếc nuối"]];
const EMOTION = Object.fromEntries(EMOTIONS);
const KIND: Record<string, string> = { buy: "Mua", sell: "Bán", hold: "Đang giữ" };
const VERDICT: Record<string, string> = { cheap: "Rẻ", fair: "Hợp lý", expensive: "Đắt" };

type Context = { price: string | null; pe: string | null; verdict: string | null; macd_d1: string | null; rsi_d1: number | null; vnindex: string | null };
type Entry = { entry_id: string; symbol: string; kind: string; created_on: string; reason: string; emotion: string | null; emotion_note: string;
  context: Partial<Context>; notes: { on: string; text: string }[]; current_price: string | null; change: string | null; imported?: Imported | null };
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
        {!e.imported && <span className="jr-move">Giá lúc ghi {formatVnd(c.price ?? null)} → nay {formatVnd(e.current_price)} (<Change value={e.change} />)</span>}
      </header>
      {e.imported && <p className="caption">Nhập từ nhật ký cũ · {e.imported.asset}{e.imported.ticker && e.imported.ticker !== e.symbol ? ` · ${e.imported.ticker}` : ""}
        {e.imported.qty ? ` · SL ${formatDecimal(e.imported.qty, 0)}` : ""}{e.imported.price ? ` · Giá vốn ${formatVnd(e.imported.price)}` : ""}
        {e.imported.total ? ` · Giá trị vốn ${formatVnd(e.imported.total)}` : ""}{e.imported.pnl ? ` · Lãi/lỗ đã ghi tay ${formatVnd(e.imported.pnl)}` : ""}</p>}
      <p className="jr-reason">{e.reason || <span className="muted">Không ghi lý do.</span>}</p>
      {e.emotion && <p className="caption">Cảm xúc lúc đó: <strong>{EMOTION[e.emotion]}</strong>{e.emotion_note && ` — ${e.emotion_note}`}</p>}
      {!e.imported && <button type="button" className="btn" aria-expanded={open} onClick={() => setOpen(!open)}>Bối cảnh lúc ghi</button>}
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

const IMPORT_HEADERS = ["Ngày giao dịch", "Lệnh", "Mã", "Loại tài sản", "SL tổng", "Giá vốn", "Giá trị vốn", "Lãi/Lỗ", "Lý do mua/ bán"];
const MAX_FILE_CHARS = 900_000;
type Preview = { rows: Entry[]; new: number; duplicates: number; problems: { line: number; message: string }[]; imported: number };

function ImportBox({ onDone }: { onDone: () => void }) {
  const [content, setContent] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const send = (text: string, commit: boolean) => api<Preview>("journal/import", { method: "POST", body: { content: text, commit, request_id: requestId().slice(0, 64) } });
  function reset() { setContent(null); setPreview(null); }
  async function choose(file: File | undefined) {
    if (!file) return;
    setMessage(null); reset();
    const text = await file.text();
    if (text.length > MAX_FILE_CHARS) { setMessage("File quá lớn (tối đa khoảng 900.000 ký tự). Hãy chia thành nhiều file."); return; }
    if (text.includes("\ufffd")) { setMessage("File không ở dạng UTF-8 nên chữ tiếng Việt bị hỏng. Hãy lưu lại dạng CSV UTF-8 rồi thử lại."); return; }
    setBusy(true);
    try { setPreview(await send(text, false)); setContent(text); } catch (e) { setMessage(failure(e, "Không đọc được file.")); } finally { setBusy(false); }
  }
  async function commit() {
    if (!content) return;
    setBusy(true);
    try {
      const done = await send(content, true);
      reset(); setMessage(`Đã nhập ${done.imported} mục.${done.problems.length ? ` ${done.problems.length} dòng lỗi không được nhập.` : ""}`); onDone();
    } catch (e) { setMessage(failure(e, "Lỗi lưu.")); } finally { setBusy(false); }
  }
  return (
    <details className="surface" aria-label="Nhập từ nhật ký cũ">
      <summary><strong>Nhập từ nhật ký cũ (Excel/CSV)</strong></summary>
      <p className="caption">Với file HTML cũ: mở file, bấm <strong>Xóa bộ lọc</strong> rồi <strong>Xuất Excel</strong>, sau đó chọn file vừa tải ở đây. Phần mềm cho xem trước, chưa lưu gì
        cho tới khi bạn bấm nhập. Mục nhập vào chỉ nằm trong Nhật ký, không thêm vào Sổ giao dịch (file cũ không có phí, thuế; lãi/lỗ là số ghi tay). Nhập lại cùng file không tạo mục trùng.</p>
      <div className="actions">
        <label className="btn"><FileUp size={16} aria-hidden="true" />Chọn file
          <input type="file" accept=".xls,.csv" aria-label="Chọn file nhật ký" hidden disabled={busy} onChange={(e) => { void choose(e.target.files?.[0]); e.target.value = ""; }} /></label>
        <button type="button" className="btn" onClick={() => download(spreadsheet("NhatKy", IMPORT_HEADERS, [["2026-01-15", "Mua", "HPG", "Cổ phiếu", 1000, 20000, null, null, "Ví dụ điền mẫu"]]), "mau-nhat-ky.xls")}>
          <Download size={16} aria-hidden="true" />Tải file mẫu</button>
      </div>
      {preview && <div role="status">
        <p><strong>{preview.new}</strong> mục mới · {preview.duplicates} mục đã có · <strong>{preview.problems.length}</strong> dòng lỗi</p>
        {preview.problems.length > 0 && <ul className="ft-checks" aria-label="Dòng lỗi">{preview.problems.map((p) => <li key={p.line}>Dòng {p.line}: {p.message}</li>)}</ul>}
        {preview.rows.length > 0 && <div className="tablewrap"><table aria-label="Xem trước nhật ký nhập">
          <thead><tr><th>Ngày</th><th>Lệnh</th><th>Mã</th><th>Tài sản</th><th className="num">Giá trị vốn</th><th>Lý do</th></tr></thead>
          <tbody>{preview.rows.slice(0, 20).map((r) => <tr key={r.entry_id}><td>{day(r.created_on)}</td><td>{KIND[r.kind]}</td><td>{r.imported?.ticker || r.symbol}</td><td>{r.imported?.asset}</td>
            <td className="num">{formatVnd(r.imported?.total ?? null)}</td><td>{r.reason}</td></tr>)}</tbody></table></div>}
        {preview.rows.length > 20 && <p className="caption">Đang hiện 20/{preview.rows.length} mục đầu.</p>}
        <div className="actions">
          {preview.new > 0 && <button type="button" className="btn primary" disabled={busy} onClick={() => void commit()}>Nhập {preview.new} mục</button>}
          <button type="button" className="btn" onClick={reset}>Hủy</button></div>
      </div>}
      {message && <p className="notice" role="status">{message}</p>}
    </details>
  );
}

function exportJournal(rows: Entry[]) {
  const headers = [...IMPORT_HEADERS, "Cảm xúc", "Ghi chú cảm xúc", "Ghi chú thêm", "Giá lúc ghi", "Giá nay", "Thay đổi"];
  const num = (v: string | null | undefined) => (v === null || v === undefined || v === "" ? null : Number(v));
  download(spreadsheet("NhatKy", headers, rows.map((e) => [e.created_on, KIND[e.kind] ?? e.kind, e.symbol, e.imported?.asset ?? "Cổ phiếu", num(e.imported?.qty), num(e.imported?.price), num(e.imported?.total),
    num(e.imported?.pnl), e.reason, e.emotion ? EMOTION[e.emotion] : "", e.emotion_note, e.notes.map((n) => `${n.on}: ${n.text}`).join(" | "), num(e.context.price), num(e.current_price), num(e.change)])),
  "nhat-ky-dau-tu.xls");
}

/** Why each decision was made and how it felt, beside where the price is now. Entries are never edited; notes are appended. */
export function JournalView() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { api<Data>("journal").then(setD, (e) => setError(failure(e, "Lỗi tải."))); }, []);
  useEffect(load, [load]);
  const [filter, setFilter] = useState<JournalFilter>(NO_FILTER);
  const shown = useMemo(() => filterEntries(d?.entries ?? [], filter), [d, filter]);
  const assets = useMemo(() => [...new Set((d?.entries ?? []).map((e) => e.imported?.asset ?? "Cổ phiếu"))].sort((a, b) => a.localeCompare(b, "vi")), [d]);
  const set = (key: keyof JournalFilter) => (e: { target: { value: string } }) => setFilter((f) => ({ ...f, [key]: e.target.value }));
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!d) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const sum = summarize(shown);
  return (
    <>
      <p className="notice">Mỗi mục lưu lý do, cảm xúc và bối cảnh thị trường lúc ghi; không sửa hay xóa, chỉ thêm ghi chú. Khi giá đi thêm
        {" "}{formatRatio(d.threshold, 1).replace(",0%", "%")} so với giá lúc ghi (lên hoặc xuống), ứng dụng nhắc qua Telegram kèm đúng lý do đã ghi. Chỉ để tự xem lại, không phải khuyến nghị.</p>
      <HoldForm held={d.held} onSaved={load} />
      <ImportBox onDone={load} />
      {d.entries.length > 0 && <section className="surface" aria-label="Tra cứu nhật ký">
        <h2>Tra cứu</h2>
        <div className="formgrid">
          <label className="field">Mã<input value={filter.symbol} maxLength={12} onChange={set("symbol")} placeholder="HPG" /></label>
          <label className="field">Lệnh<select value={filter.kind} onChange={set("kind")}><option value="">Tất cả</option>
            {Object.entries(KIND).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="field">Cảm xúc<select value={filter.emotion} onChange={set("emotion")}><option value="">Tất cả</option>
            {EMOTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="field">Loại tài sản<select value={filter.asset} onChange={set("asset")}><option value="">Tất cả</option>
            {assets.map((a) => <option key={a} value={a}>{a}</option>)}</select></label>
          <label className="field">Từ khóa trong lý do, ghi chú<input value={filter.text} onChange={set("text")} /></label>
          <label className="field">Từ ngày<input type="date" value={filter.from} onChange={set("from")} /></label>
          <label className="field">Đến ngày<input type="date" value={filter.to} onChange={set("to")} /></label>
        </div>
        <p className="caption" role="status">{sum.count}/{d.entries.length} mục
          {sum.average !== null && <> · thay đổi giá trung bình từ lúc ghi {sum.average >= 0 ? "+" : ""}{formatRatio(String(sum.average), 1)} ({sum.withChange} mục có giá)</>}
          {sum.pnl !== null && <> · lãi/lỗ ghi tay trong mục nhập từ file cũ {formatVnd(String(sum.pnl))} ({sum.withPnl} mục)</>}</p>
        <div className="actions">
          <button type="button" className="btn" onClick={() => setFilter(NO_FILTER)}>Xóa bộ lọc</button>
          <button type="button" className="btn" disabled={shown.length === 0} onClick={() => exportJournal(shown)}><Download size={16} aria-hidden="true" />Xuất Excel</button></div>
      </section>}
      {d.entries.length === 0 ? <p className="muted">Chưa có mục nào. Ghi lý do khi nhập giao dịch mua/bán, ghi lý do đang giữ ở trên, hoặc nhập từ nhật ký cũ.</p>
        : shown.length === 0 ? <p className="muted">Không có mục nào khớp bộ lọc.</p>
        : shown.map((e) => <EntryCard key={e.entry_id} e={e} onChanged={load} />)}
    </>
  );
}
