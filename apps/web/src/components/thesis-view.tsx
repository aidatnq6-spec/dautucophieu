"use client";
import { useCallback, useEffect, useState } from "react";
import { PauseCircle, Pencil, Plus, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal } from "../lib/format";
import { EMOTIONS } from "./journal-view";
import { levelInput } from "./price-alerts";

type View = { state: "ok" | "broken" | "unknown"; reading: string | null; reason: string | null };
type Cond = { id: string; kind: string; params: Record<string, string | number>; label: string; view: View; status: string | null;
  broken_on: string | null; broken_price: string | null; set_on: string; hold: { until: string; reason: string } | null };
type Thesis = { id: string; symbol: string; reasons: string[]; note: string; created_on: string; conditions: Cond[]; company: string | null };
type Kind = { label: string; params: string[]; applies: string | null };
type Data = { version: number; theses: Thesis[]; missing: string[]; kinds: Record<string, Kind>; reasons: Record<string, string> };
type Draft = { id?: string; kind: string; values: Record<string, string> };

const PARAM: Record<string, string> = { pct: "%", level: "mức giá (nghìn đồng)", n: "ngưỡng" };
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const failure = (e: unknown, fallback: string) => (e instanceof ApiError ? e.failure.message : fallback);

/** What the owner typed for a condition, as the API takes it; null when it is not acceptable (the server checks again). */
export function conditionParams(names: string[], values: Record<string, string>): Record<string, string | number> | null {
  const out: Record<string, string | number> = {};
  for (const name of names) {
    const raw = (values[name] ?? "").trim();
    if (name === "n") {
      if (!/^\d$/.test(raw)) return null;
      out.n = Number(raw);
    } else {
      const v = levelInput(raw);
      if (v === null || (name === "pct" && (Number(v) < 1 || Number(v) > 90))) return null;
      out[name] = v;
    }
  }
  return out;
}

export function stateText(view: View, brokenOn: string | null): { text: string; tone: "good" | "bad" | "warn" } {
  if (view.state === "ok") return { text: "Đạt", tone: "good" };
  if (view.state === "broken") return { text: brokenOn ? `Bị phá từ ${day(brokenOn)}` : "Bị phá", tone: "bad" };
  return { text: "Chưa kiểm được", tone: "warn" };
}

function ConditionFields({ draft, kinds, company, onChange, onRemove }: { draft: Draft; kinds: Record<string, Kind>; company: string | null;
  onChange: (d: Draft) => void; onRemove?: () => void }) {
  const kind = kinds[draft.kind];
  return (
    <div className="th-cond">
      <label className="field">Điều kiện<select value={draft.kind} onChange={(e) => onChange({ ...draft, kind: e.target.value, values: {} })}>
        {Object.entries(kinds).filter(([, k]) => k.applies === null || company === null || k.applies === company)
          .map(([id, k]) => <option key={id} value={id}>{k.label}</option>)}</select></label>
      {kind?.params.map((name) => <label key={name} className="field">{PARAM[name]}<input inputMode="decimal" value={draft.values[name] ?? ""}
        onChange={(e) => onChange({ ...draft, values: { ...draft.values, [name]: e.target.value } })} /></label>)}
      {onRemove && <button type="button" className="btn" aria-label="Bỏ điều kiện này" onClick={onRemove}><Trash2 size={15} aria-hidden="true" /></button>}
    </div>
  );
}

function ThesisForm({ data, symbol, thesis, onSave, onCancel }: { data: Data; symbol: string; thesis?: Thesis;
  onSave: (body: Record<string, unknown>) => Promise<boolean>; onCancel: () => void }) {
  const company = thesis?.company ?? null;
  const [reasons, setReasons] = useState<string[]>(thesis?.reasons ?? []);
  const [note, setNote] = useState(thesis?.note ?? "");
  const [drafts, setDrafts] = useState<Draft[]>(thesis?.conditions.map((c) => ({ id: c.id, kind: c.kind,
    values: Object.fromEntries(Object.entries(c.params).map(([k, v]) => [k, String(v).replace(".", ",")])) })) ?? [{ kind: "loss_vs_cost", values: {} }]);
  const params = drafts.map((d) => conditionParams(data.kinds[d.kind]?.params ?? [], d.values));
  const locked = new Set(thesis?.conditions.filter((c) => c.status === "broken").map((c) => c.id) ?? []);
  const fomoWithoutLimit = reasons.includes("fomo") && !drafts.some((d) => d.kind === "loss_vs_cost");
  const ready = reasons.length > 0 && drafts.length > 0 && params.every((p) => p !== null) && !fomoWithoutLimit;
  return (
    <form className="th-form" aria-label={`Luận điểm ${symbol}`} onSubmit={(e) => {
      e.preventDefault();
      if (ready) void onSave({ reasons, note, conditions: drafts.map((d, i) => ({ ...(d.id ? { id: d.id } : {}), kind: d.kind, params: params[i] })) });
    }}>
      <fieldset><legend>Lý do mua</legend>
        {Object.entries(data.reasons).map(([id, label]) => <label key={id} className="th-check"><input type="checkbox" checked={reasons.includes(id)}
          onChange={(e) => setReasons(e.target.checked ? [...reasons, id] : reasons.filter((r) => r !== id))} />{label}</label>)}
      </fieldset>
      <label className="field">Vì sao mua, điều gì xảy ra thì bạn đã sai<textarea value={note} maxLength={2000} rows={3} onChange={(e) => setNote(e.target.value)} /></label>
      {drafts.map((d, i) => locked.has(d.id ?? "")
        ? <p key={d.id} className="caption">Điều kiện đã bị phá — {thesis?.conditions.find((c) => c.id === d.id)?.label}: chỉ thay đổi qua “Giữ tiếp, có lý do”.</p>
        : <ConditionFields key={d.id ?? `new-${i}`} draft={d} kinds={data.kinds} company={company}
          onChange={(next) => setDrafts(drafts.map((x, j) => (j === i ? next : x)))} onRemove={() => setDrafts(drafts.filter((_, j) => j !== i))} />)}
      <button type="button" className="btn" onClick={() => setDrafts([...drafts, { kind: "f_score", values: {} }])}><Plus size={15} aria-hidden="true" />Thêm điều kiện</button>
      {fomoWithoutLimit && <p className="notice" role="alert">Mua vì sợ bỏ lỡ thì cần đặt điều kiện “Lỗ so với giá vốn”.</p>}
      <div className="row"><button className="btn primary" type="submit" disabled={!ready}>Lưu luận điểm</button>
        <button className="btn" type="button" onClick={onCancel}>Hủy</button></div>
    </form>
  );
}

function HoldForm({ data, thesis, cond, onSave, onCancel }: { data: Data; thesis: Thesis; cond: Cond;
  onSave: (body: Record<string, unknown>) => Promise<boolean>; onCancel: () => void }) {
  const [reason, setReason] = useState("");
  const [emotion, setEmotion] = useState("");
  const [mode, setMode] = useState<"date" | "condition">("date");
  const [until, setUntil] = useState("");
  const [draft, setDraft] = useState<Draft>({ kind: cond.kind, values: {} });
  const params = conditionParams(data.kinds[draft.kind]?.params ?? [], draft.values);
  const ready = reason.trim() !== "" && (mode === "date" ? until !== "" : params !== null);
  return (
    <form className="th-form" aria-label={`Giữ tiếp ${thesis.symbol}`} onSubmit={(e) => {
      e.preventDefault();
      if (ready) void onSave({ action: "hold", thesis_id: thesis.id, cond_id: cond.id, reason, emotion: emotion || null,
        ...(mode === "date" ? { until } : { new_condition: { kind: draft.kind, params } }) });
    }}>
      <p className="caption">Giữ tiếp khi “{cond.label}” đã bị phá. Lý do được ghi vào Nhật ký để sau này hậu kiểm.</p>
      <label className="field">Vì sao vẫn giữ<textarea value={reason} maxLength={2000} rows={3} onChange={(e) => setReason(e.target.value)} /></label>
      <label className="field">Cảm xúc lúc này<select value={emotion} onChange={(e) => setEmotion(e.target.value)}>
        <option value="">Không ghi</option>{EMOTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      <fieldset><legend>Rồi sao nữa</legend>
        <label className="th-check"><input type="radio" checked={mode === "date"} onChange={() => setMode("date")} />Ngày xem lại (tối đa 90 ngày)</label>
        <label className="th-check"><input type="radio" checked={mode === "condition"} onChange={() => setMode("condition")} />Điều kiện mới thay điều kiện này</label>
      </fieldset>
      {mode === "date" ? <label className="field">Ngày xem lại<input type="date" value={until} onChange={(e) => setUntil(e.target.value)} /></label>
        : <ConditionFields draft={draft} kinds={data.kinds} company={thesis.company} onChange={setDraft} />}
      <div className="row"><button className="btn primary" type="submit" disabled={!ready}>Giữ tiếp</button>
        <button className="btn" type="button" onClick={onCancel}>Hủy</button></div>
    </form>
  );
}

/** Luận điểm đầu tư: why each held ticker was bought and the conditions that would say the owner was wrong. */
export function ThesisView() {
  const [data, setData] = useState<Data | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [open, setOpen] = useState<{ symbol: string; thesis?: Thesis } | null>(null);
  const [holding, setHolding] = useState<{ thesis: Thesis; cond: Cond } | null>(null);
  const load = useCallback(() => api<Data>("theses").then(setData, (e) => setMessage(failure(e, "Lỗi tải luận điểm."))), []);
  useEffect(() => { void load(); }, [load]);

  async function change(body: Record<string, unknown>) {
    if (!data) return false;
    try {
      setData(await api<Data>("theses", { method: "PUT", body: { ...body, expected_version: data.version, request_id: requestId() } }));
      setMessage(null); setOpen(null); setHolding(null);
      return true;
    } catch (e) {
      setMessage(failure(e, "Lỗi lưu luận điểm."));
      return false;
    }
  }
  return (
    <section className="surface" aria-label="Luận điểm đầu tư">
      <h2>Luận điểm đầu tư</h2>
      <p className="caption">Lúc còn tỉnh táo, ghi vì sao mua và điều gì xảy ra thì bạn đã sai. Phần mềm tự kiểm (lỗ so với giá vốn mỗi 5 phút trong phiên,
        các điều kiện khác sau giờ đóng cửa) và nhắn Telegram khi một điều kiện bị phá. Điều kiện đã bị phá giữ nguyên trạng thái kể cả khi giá hồi;
        muốn dừng nhắc thì bán, hoặc “Giữ tiếp, có lý do”. Không phải khuyến nghị.</p>
      {message && <p className="errors" role="alert">{message}</p>}
      {!data && !message && <p className="muted fx-loading" role="status">Đang tải luận điểm…</p>}
      {data && <>
        {data.missing.map((s) => <div key={s} className="th-card" data-testid={`thesis-missing-${s}`}>
          <div className="row"><strong>{s}</strong><span className="pill warn">Chưa có luận điểm</span>
            {open?.symbol !== s && <button className="btn" type="button" onClick={() => setOpen({ symbol: s })}><Plus size={15} aria-hidden="true" />Đặt luận điểm</button>}</div>
          {open?.symbol === s && !open.thesis && <ThesisForm data={data} symbol={s} onSave={(b) => change({ action: "save", symbol: s, ...b })} onCancel={() => setOpen(null)} />}
        </div>)}
        {data.theses.map((t) => <article key={t.id} className="th-card" aria-label={`Luận điểm ${t.symbol}`}>
          <div className="row"><strong>{t.symbol}</strong><span className="caption">đặt {day(t.created_on)} · {t.reasons.map((r) => data.reasons[r]).join(", ")}</span>
            {open?.thesis?.id !== t.id && <button className="btn" type="button" onClick={() => setOpen({ symbol: t.symbol, thesis: t })}><Pencil size={15} aria-hidden="true" />Sửa</button>}</div>
          {t.note && <p className="th-note">“{t.note}”</p>}
          {open?.thesis?.id === t.id ? <ThesisForm data={data} symbol={t.symbol} thesis={t} onSave={(b) => change({ action: "edit", thesis_id: t.id, ...b })}
            onCancel={() => setOpen(null)} /> : <ul className="th-conds">
            {t.conditions.map((c) => {
              const s = stateText(c.view, c.broken_on);
              return <li key={c.id}>
                <span>{c.label}</span><span className={`pill ${s.tone}`}>{s.text}</span>
                <span className="caption">{c.view.reading ?? c.view.reason ?? ""}{c.broken_price && c.view.state === "broken"
                  ? ` · lúc báo đầu ${formatDecimal(String(Number(c.broken_price) / 1000), 2)}` : ""}</span>
                {c.hold && <span className="caption">Giữ tiếp đến {day(c.hold.until)}: “{c.hold.reason}”</span>}
                {c.status === "broken" && !c.hold && <button className="btn" type="button" onClick={() => setHolding({ thesis: t, cond: c })}>
                  <PauseCircle size={15} aria-hidden="true" />Giữ tiếp, có lý do</button>}
                {holding?.cond.id === c.id && <HoldForm data={data} thesis={t} cond={c} onSave={change} onCancel={() => setHolding(null)} />}
              </li>;
            })}
          </ul>}
        </article>)}
        {data.theses.length === 0 && data.missing.length === 0 && <p className="muted">Chưa có cổ phiếu trong sổ.</p>}
      </>}
    </section>
  );
}
