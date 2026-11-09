"use client";
import { useEffect, useState } from "react";
import { CalendarCheck, Pencil, Plus, Trash2, X } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd, groupDigitsInput, hanoiDate, parseMoneyInput } from "../lib/format";

type Plan = { id: string; name: string; asset: "gold" | "fund"; day: number; start: string; chi: string | null; amount: string | null; kind: string | null; fund: string | null };
type Buy = { id: string; plan: string; on: string; amount: string; quantity: string; book_row?: string | null };
type Month = { month: string; got: string; status: "met" | "short" | "none" | "pending"; short_by: string | null };
type Status = { id: string; months: Month[]; streak: number; cost: string; quantity: string; average: string | null; price: string | null; price_on: string | null; stale: boolean; value: string | null; change: string | null;
  price_reason: "no_buys" | "no_kind" | "no_price" | null; book_rows: { id: string; name: string }[] };
type View = { version: number; book_exists: boolean; data: { plans: Plan[]; buys: Buy[] }; plans: Status[]; gold_kinds: string[]; gold_source: string | null; nav_source: string | null };
type Draft = { id: string | null; name: string; asset: "gold" | "fund"; day: string; start: string; size: string; kind: string; fund: string };

const BLANK: Draft = { id: null, name: "", asset: "gold", day: "", start: "", size: "", kind: "", fund: "" };
const STATUS: Record<Month["status"], [string, string]> = { met: ["đã mua", "good"], short: ["thiếu", "warn"], none: ["chưa mua", "bad"], pending: ["đang chờ", ""] };
const label = (key: string) => `${key.slice(5, 7)}/${key.slice(0, 4)}`;
const day = (d: string) => `${d.slice(8)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;
const qty = (v: string) => { const [i, f] = v.split("."); return formatVnd(i, { unit: false }) + (f ? `,${f}` : ""); };
const quantity = (raw: string) => { const v = parseMoneyInput(raw); return v !== null && Number(v) > 0 && (v.split(".")[1] ?? "").length <= 4 ? v : null; };

function PlanCard({ plan, status, buys, busy, onBuy, onDelete, onEdit, onRemove, source, bookExists, onPost }: { plan: Plan; status: Status; buys: Buy[]; busy: boolean; source: string | null; onBuy: (b: Omit<Buy, "id" | "plan">) => Promise<boolean>;
  bookExists: boolean; onPost: (b: Buy, row: string | null) => void;
  onDelete: (b: Buy) => void; onEdit: () => void; onRemove: () => void }) {
  const [on, setOn] = useState(hanoiDate());
  const [amount, setAmount] = useState("");
  const [count, setCount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pick, setPick] = useState<string | null>(null);  // null: the first row that fits; "": a new row
  const gold = plan.asset === "gold", unit = gold ? "chỉ" : "đơn vị";
  const target = pick ?? status.book_rows[0]?.id ?? "";
  const waiting = buys.filter((b) => !b.book_row).length;
  const [open, setOpen] = useState(waiting > 0 && bookExists);  // stays open after adding one, so its mark can be seen
  function post(b: Buy) {
    const where = status.book_rows.find((r) => r.id === target)?.name;
    if (window.confirm(`Cộng ${formatVnd(b.amount)} và ${qty(b.quantity)} ${unit} (mua ngày ${day(b.on)}) vào ${where ? `dòng "${where}"` : `dòng mới "${plan.name}"`} của Sổ tài sản? Tháp tài sản sẽ tính lại.`)) onPost(b, target || null);
  }
  async function submit() {
    const a = parseMoneyInput(amount), q = quantity(count);
    if (!on || a === null || a.includes(".") || a === "0" || q === null) { setError(`Nhập ngày mua, tiền bỏ ra (đồng) và số ${unit} lớn hơn 0.`); return; }
    if (await onBuy({ on, amount: a, quantity: q })) { setAmount(""); setCount(""); setError(null); if (bookExists) setOpen(true); }
  }
  const why = { no_buys: "Chưa có lần mua nào.", no_kind: gold ? "Chưa chọn loại giá nên chưa tính giá trị hiện tại." : "Chưa nhập mã quỹ nên chưa tính giá trị hiện tại.", no_price: gold ? "Bảng giá không có loại này nên chưa tính giá trị hiện tại." : "Chưa có NAV của quỹ này nên chưa tính giá trị hiện tại." };
  const change = status.change === null ? null : Number(status.change);
  return (
    <article className="ta-card" aria-label={plan.name}>
      <div className="row"><h3>{plan.name}</h3><span className="db-actions">
        <button type="button" className="btn" aria-label={`Sửa ${plan.name}`} disabled={busy} onClick={onEdit}><Pencil size={14} aria-hidden="true" />Sửa</button>
        <button type="button" className="btn" aria-label={`Xóa ${plan.name}`} disabled={busy} onClick={onRemove}><Trash2 size={14} aria-hidden="true" />Xóa</button></span></div>
      <p className="caption">{gold ? `${qty(plan.chi!)} chỉ` : formatVnd(plan.amount!)} mỗi tháng, ngày {plan.day}, từ {label(plan.start)} · Chuỗi liên tục: <strong>{status.streak} tháng</strong></p>
      {status.months.length === 0 ? <p className="muted">Kế hoạch bắt đầu từ {label(plan.start)}.</p> : <ol className="contrib-months" aria-label={`Các tháng của ${plan.name}`}>{status.months.slice(-12).map((m) => {
        const [word, tone] = STATUS[m.status];
        return <li key={m.month} data-testid={`ta-month-${m.month}`}><span>{label(m.month)}</span><span className={`pill ${tone}`}>{word}{m.short_by ? ` ${gold ? `${qty(m.short_by)} chỉ` : formatVnd(m.short_by)}` : ""}</span></li>;
      })}</ol>}
      <dl className="eb-result">
        <div><dt>Đã mua</dt><dd>{qty(status.quantity)} {unit} · {formatVnd(status.cost)}</dd></div>
        <div className="eb-main"><dt>Giá vốn bình quân/{unit}</dt><dd data-testid="ta-average">{status.average === null ? "Chưa có" : formatVnd(status.average)}</dd></div>
        {status.price !== null && <div><dt>{gold ? "Giá mua vào" : "NAV"}{source ? ` ${source}` : ""} ngày {day(status.price_on!)}{status.stale ? " (đã cũ)" : ""}</dt><dd>{formatVnd(status.price)}/{unit}</dd></div>}
        {status.value !== null && <div><dt>Giá trị hiện tại</dt><dd>{formatVnd(status.value)} <span className={change! >= 0 ? "positive" : "negative"}>{change! >= 0 ? "+" : "−"}{formatVnd(String(Math.abs(change!)))}</span></dd></div>}
      </dl>
      {status.price_reason && status.price_reason !== "no_buys" && <p className="caption">{why[status.price_reason]}</p>}
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
        <label className="field">Ngày mua<input type="date" value={on} disabled={busy} onChange={(e) => setOn(e.target.value)} /></label>
        <label className="field">Tiền bỏ ra (đ)<input inputMode="numeric" value={amount} disabled={busy} onChange={(e) => setAmount(groupDigitsInput(e.target.value))} /></label>
        <label className="field">{gold ? "Số chỉ mua" : "Số đơn vị mua"}<input inputMode="decimal" value={count} disabled={busy} onChange={(e) => setCount(e.target.value)} /></label>
        <button type="submit" className="btn" disabled={busy}><Plus size={14} aria-hidden="true" />Ghi lần mua</button>
      </form>
      {error && <p className="errors" role="alert">{error}</p>}
      {waiting > 0 && (bookExists ? <label className="field">Cộng vào dòng<select value={target} disabled={busy} onChange={(e) => setPick(e.target.value)}>
        {status.book_rows.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}<option value="">Tạo dòng mới “{plan.name}”</option></select></label>
        : <p className="caption">Sổ tài sản chưa có dữ liệu nên chưa cộng được: nhập Sổ tài sản trước.</p>)}
      {buys.length > 0 && <details className="mc-table" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}><summary>Các lần mua ({buys.length})</summary>
        <table className="fv-table" aria-label={`Các lần mua của ${plan.name}`}><thead><tr><th>Ngày</th><th className="num">Tiền bỏ ra</th><th className="num">Số lượng</th><th className="num">Giá mua/{unit}</th><th /></tr></thead>
          <tbody>{[...buys].sort((a, b) => b.on.localeCompare(a.on)).map((b) => <tr key={b.id}><td data-label="Ngày">{day(b.on)}</td><td data-label="Tiền bỏ ra" className="num">{formatVnd(b.amount)}</td><td data-label="Số lượng" className="num">{qty(b.quantity)}</td>
            <td data-label="Giá mua" className="num">{formatVnd(String(Math.round(Number(b.amount) / Number(b.quantity))))}</td>
            <td className="db-actions">{b.book_row ? <span className="pill good">đã cộng vào Sổ</span> : bookExists && <button type="button" className="btn" disabled={busy} onClick={() => post(b)}><Plus size={14} aria-hidden="true" />Cộng vào Sổ tài sản</button>}
              <button type="button" className="btn" aria-label={`Xóa lần mua ${day(b.on)}`} disabled={busy} onClick={() => onDelete(b)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td></tr>)}</tbody></table>
      </details>}
    </article>
  );
}

/** Fixed monthly purchases of gold or a fund: each purchase recorded, the months met, the average cost. Reminders go by Telegram; a purchase reaches Sổ tài sản only when the owner adds it there. */
export function Accumulation({ onPosted }: { onPosted?: () => void } = {}) {
  const [view, setView] = useState<View | null>(null);
  const [draft, setDraft] = useState<Draft>(BLANK);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("accumulation").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function put(plans: Plan[], buys: Buy[]): Promise<boolean> {
    if (!view) return false;
    setBusy(true);
    try {
      setView(await api<View>("accumulation", { method: "PUT", body: { plans, buys, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      return true;
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); return false; }
    finally { setBusy(false); }
  }
  async function savePlan() {
    if (!view) return;
    const d = Number(draft.day), gold = draft.asset === "gold", fund = draft.fund.trim().toUpperCase();
    const size = gold ? quantity(draft.size) : parseMoneyInput(draft.size);
    if (!draft.name.trim() || !Number.isInteger(d) || d < 1 || d > 28 || !/^\d{4}-\d{2}$/.test(draft.start)) { setMessage("Nhập tên, ngày mua từ 1 đến 28 và tháng bắt đầu."); return; }
    if (size === null || (!gold && (size.includes(".") || size === "0"))) { setMessage(gold ? "Số chỉ mỗi tháng lớn hơn 0, tối đa 4 chữ số thập phân." : "Số tiền mỗi tháng là số đồng lớn hơn 0."); return; }
    if (fund && !/^[A-Z0-9][A-Z0-9-]{1,15}$/.test(fund)) { setMessage("Mã quỹ như trên Fmarket, ví dụ VFF hoặc VCBF-FIF."); return; }
    const row: Plan = { id: draft.id ?? requestId(), name: draft.name.trim(), asset: draft.asset, day: d, start: draft.start, chi: gold ? size : null, amount: gold ? null : size, kind: gold && draft.kind ? draft.kind : null, fund: !gold && fund ? fund : null };
    const plans = view.data.plans.some((p) => p.id === row.id) ? view.data.plans.map((p) => (p.id === row.id ? row : p)) : [...view.data.plans, row];
    if (await put(plans, view.data.buys)) setDraft(BLANK);
  }
  const edit = (p: Plan) => { setMessage(null); setDraft({ id: p.id, name: p.name, asset: p.asset, day: String(p.day), start: p.start, size: p.asset === "gold" ? qty(p.chi!) : formatVnd(p.amount!, { unit: false }), kind: p.kind ?? "", fund: p.fund ?? "" }); };
  function removePlan(p: Plan) {
    if (!view || !window.confirm(`Xóa kế hoạch "${p.name}" và toàn bộ lần mua đã ghi của nó?`)) return;
    void put(view.data.plans.filter((x) => x.id !== p.id), view.data.buys.filter((b) => b.plan !== p.id));
  }
  async function post(b: Buy, row: string | null) {
    if (!view) return;
    setBusy(true);
    try {
      setView(await api<View>("accumulation/post", { method: "POST", body: { buy: b.id, row, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      onPosted?.();
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
    finally { setBusy(false); }
  }
  function removeBuy(b: Buy) {
    if (!view || !window.confirm(b.book_row ? `Xóa lần mua ngày ${day(b.on)}? Lần này đã cộng vào Sổ tài sản; số ở Sổ không tự trừ, bạn cần sửa lại ở đó.` : `Xóa lần mua ngày ${day(b.on)}?`)) return;
    void put(view.data.plans, view.data.buys.filter((x) => x.id !== b.id));
  }
  const set = (patch: Partial<Draft>) => setDraft((old) => ({ ...old, ...patch }));
  const gold = draft.asset === "gold", kinds = view?.gold_kinds ?? [];
  return (
    <section className="surface" aria-label="Kế hoạch tích sản">
      <h2>Kế hoạch tích sản</h2>
      <p className="caption wrap">Mỗi tháng mua đều một khoản vàng hoặc chứng chỉ quỹ. Ghi từng lần mua để xem tháng nào đã mua và giá vốn bình quân của các lần đã ghi; đến ngày mà tháng đó chưa đủ, ứng dụng nhắc qua Telegram một lần và hiện ở Việc cần xem. Lần mua không tự vào Sổ tài sản: bấm Cộng vào Sổ tài sản ở từng lần mua nếu muốn cộng tiền và số lượng vào một dòng của Sổ, khi đó Tháp tài sản tính lại. Không phải khuyến nghị.</p>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void savePlan(); }}>
        <label className="field">Tên kế hoạch<input maxLength={60} value={draft.name} disabled={!view || busy} onChange={(e) => set({ name: e.target.value })} /></label>
        <label className="field">Loại tài sản<select value={draft.asset} disabled={!view || busy || draft.id !== null} onChange={(e) => set({ asset: e.target.value as Draft["asset"], size: "" })}><option value="gold">Vàng</option><option value="fund">Chứng chỉ quỹ</option></select></label>
        {gold ? <label className="field">Số chỉ mỗi tháng<input inputMode="decimal" value={draft.size} disabled={!view || busy} onChange={(e) => set({ size: e.target.value })} /></label>
          : <label className="field">Số tiền mỗi tháng (đ)<input inputMode="numeric" value={draft.size} disabled={!view || busy} onChange={(e) => set({ size: groupDigitsInput(e.target.value) })} /></label>}
        <label className="field">Ngày mua trong tháng<input inputMode="numeric" maxLength={2} value={draft.day} disabled={!view || busy} onChange={(e) => set({ day: e.target.value.replace(/\D/g, "") })} /></label>
        <label className="field">Bắt đầu từ tháng<input type="month" value={draft.start} disabled={!view || busy} onChange={(e) => set({ start: e.target.value })} /></label>
        {gold ? <label className="field">Loại giá<select value={draft.kind} disabled={!view || busy} onChange={(e) => set({ kind: e.target.value })}><option value="">Không theo giá</option>{draft.kind && !kinds.includes(draft.kind) && <option value={draft.kind}>{draft.kind} (không còn trong bảng giá)</option>}{kinds.map((k) => <option key={k} value={k}>{k}</option>)}</select></label>
          : <label className="field">Mã quỹ<input maxLength={16} value={draft.fund} placeholder="ví dụ VFF" disabled={!view || busy} onChange={(e) => set({ fund: e.target.value.toUpperCase() })} /></label>}
        <button type="submit" className="btn primary" disabled={!view || busy}><CalendarCheck size={16} aria-hidden="true" />Lưu kế hoạch tích sản</button>
        {draft.id && <button type="button" className="btn" disabled={busy} onClick={() => { setDraft(BLANK); setMessage(null); }}><X size={14} aria-hidden="true" />Hủy sửa</button>}
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {view && view.data.plans.length === 0 && <p className="muted">Chưa có kế hoạch nào.</p>}
      {view?.data.plans.map((p) => <PlanCard key={p.id} plan={p} status={view.plans.find((s) => s.id === p.id)!} buys={view.data.buys.filter((b) => b.plan === p.id)} busy={busy} source={p.asset === "gold" ? view.gold_source : view.nav_source} bookExists={view.book_exists} onPost={(b, row) => void post(b, row)}
        onBuy={(b) => put(view.data.plans, [...view.data.buys, { ...b, id: requestId(), plan: p.id }])} onDelete={removeBuy} onEdit={() => edit(p)} onRemove={() => removePlan(p)} />)}
    </section>
  );
}
