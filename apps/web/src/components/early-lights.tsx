"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";

type Option = { id: string; label: string; tier: string; unit: string };
type Row = Option & { bad: string; good: string; value: string | null; date: string | null; state: "bad" | "watch" | "good" | "none"; note: string | null };
type View = { symbol: string; version: number; catalog: Option[]; rows: Row[] };

const STATE = { bad: "Xấu", watch: "Theo dõi", good: "Tốt", none: "—" };
const CLS = { bad: "negative", watch: "", good: "positive", none: "muted" };
const n = (v: string) => v.replace(".", ",");

/** How the owner's two thresholds read, in the direction they were written: a good level above the bad one means higher is better. */
export function bands(bad: string, good: string, unit: string): { bad: string; watch: string; good: string } {
  const up = Number(good) > Number(bad);
  return { bad: `${up ? "<" : ">"} ${n(bad)}${unit}`, watch: `${n(up ? bad : good)}–${n(up ? good : bad)}${unit}`, good: `${up ? "≥" : "≤"} ${n(good)}${unit}` };
}

const period = (d: string | null) => (!d ? "" : d.includes("-Q") ? `Q${d.slice(-1)}/${d.slice(0, 4)}` : d.split("-").reverse().join("/"));

/** The owner's own early-warning board for one ticker: chosen indicators against thresholds they set. */
export function EarlyLights({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [id, setId] = useState("");
  const [bad, setBad] = useState("");
  const [good, setGood] = useState("");
  useEffect(() => { api<View>(`lights/${encodeURIComponent(symbol)}`).then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [symbol]);
  if (!view) return message ? <p className="errors" role="alert">{message}</p> : <p className="muted" role="status">Đang tải…</p>;
  async function save(rules: { id: string; bad: string; good: string }[]) {
    try {
      setView(await api<View>(`lights/${encodeURIComponent(symbol)}`, { method: "PUT", body: { rules, expected_version: view!.version, request_id: requestId() } }));
      setMessage(null); setId(""); setBad(""); setGood("");
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Không lưu được."); }
  }
  const rules = view.rows.map((r) => ({ id: r.id, bad: r.bad, good: r.good }));
  const free = view.catalog.filter((c) => !rules.some((r) => r.id === c.id));
  const tiers = [...new Set(free.map((c) => c.tier))];
  return (
    <div>
      {view.rows.length === 0 ? <p className="muted">Chưa có chỉ báo nào. Chọn chỉ báo và đặt hai ngưỡng ở dưới.</p> : <div className="tablewrap"><table aria-label={`Bảng đèn ${symbol}`}>
        <thead><tr><th>Chỉ báo</th><th>Tầng</th><th className="num">Hiện tại</th><th>Đèn</th><th>Xấu</th><th>Theo dõi</th><th>Tốt</th><th /></tr></thead>
        <tbody>{view.rows.map((r) => { const b = bands(r.bad, r.good, r.unit); return <tr key={r.id}><td>{r.label}</td><td>{r.tier}</td>
          <td className="num">{r.value === null ? "—" : `${n(r.value)}${r.unit}`}{r.date && <span className="caption"> {period(r.date)}</span>}</td>
          <td className={CLS[r.state]} title={r.note ?? undefined}><strong>{STATE[r.state]}</strong>{r.note && <span className="caption"> {r.note}</span>}</td>
          <td>{b.bad}</td><td>{b.watch}</td><td>{b.good}</td>
          <td><button type="button" className="btn" aria-label={`Bỏ ${r.label}`} onClick={() => void save(rules.filter((x) => x.id !== r.id))}><Trash2 size={14} aria-hidden="true" /></button></td></tr>; })}</tbody>
      </table></div>}
      <form className="eb-form" aria-label="Thêm chỉ báo" onSubmit={(e) => { e.preventDefault(); void save([...rules, { id, bad: bad.trim(), good: good.trim() }]); }}>
        <label className="field">Chỉ báo<select value={id} onChange={(e) => setId(e.target.value)}><option value="">Chọn…</option>
          {tiers.map((t) => <optgroup key={t} label={t}>{free.filter((c) => c.tier === t).map((c) => <option key={c.id} value={c.id}>{c.label}{c.unit ? ` (${c.unit})` : ""}</option>)}</optgroup>)}</select></label>
        <label className="field">Ngưỡng Xấu<input inputMode="decimal" value={bad} onChange={(e) => setBad(e.target.value)} /></label>
        <label className="field">Ngưỡng Tốt<input inputMode="decimal" value={good} onChange={(e) => setGood(e.target.value)} /></label>
        <button type="submit" className="btn primary" disabled={!id || !bad.trim() || !good.trim() || view.rows.length >= 12}><Plus size={15} aria-hidden="true" />Thêm</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      <p className="caption">Ngưỡng do bạn đặt: Tốt lớn hơn Xấu nghĩa là càng cao càng tốt, Tốt nhỏ hơn Xấu nghĩa là càng thấp càng tốt. Chỉ số phần trăm nhập theo %. Số quá cũ (hơn 120 ngày) hoặc chưa có thì không tô màu. Khi đèn đổi màu, phần mềm báo qua Telegram sau lượt chạy tối. Không phải khuyến nghị.</p>
    </div>
  );
}
