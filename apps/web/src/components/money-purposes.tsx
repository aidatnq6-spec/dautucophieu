"use client";
import { useEffect, useState } from "react";
import { Plus, Tags, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd } from "../lib/format";

export type Purpose = { id: string; name: string; given: boolean };
type Row = { id: string; kind: "account" | "deposit" | "bond" | "gold" | "crypto"; name: string; value: string; at_cost: boolean };
type Total = Purpose & { total: string; count: number };
export type PurposesView = { version: number; data: { purposes: Purpose[]; tags: Record<string, string> }; rows: Row[];
  view: { purposes: Total[]; unassigned: { total: string; count: number }; total: string; given_total: string; mine_total: string } };

const KIND: Record<Row["kind"], string> = { account: "Tiền mặt", deposit: "Sổ tiền gửi", bond: "Trái phiếu, quỹ", gold: "Vàng", crypto: "Tiền số" };
const SUGGESTED = ["Quỹ dự phòng", "Quỹ mua nhà", "Cho con", "Đầu tư dài hạn"];
const NEW = "__new__";

/** A purpose picked from the list, or a new one named on the spot (returned so the caller saves it with the tag). */
export function PurposeSelect({ label, value, purposes, disabled, onPick }: { label: string; value: string; purposes: Purpose[]; disabled?: boolean;
  onPick: (id: string, created?: Purpose) => void }) {
  return (
    <select aria-label={label} value={value} disabled={disabled} onChange={(e) => {
      if (e.target.value !== NEW) { onPick(e.target.value); return; }
      const name = window.prompt("Tên mục đích mới")?.trim().slice(0, 40);
      if (!name) return;
      const same = purposes.find((p) => p.name.toLowerCase() === name.toLowerCase());
      if (same) { onPick(same.id); return; }
      const created = { id: requestId(), name, given: false };
      onPick(created.id, created);
    }}>
      <option value="">Chưa gắn</option>
      {purposes.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      <option value={NEW}>+ Tạo mục đích mới…</option>
    </select>
  );
}

/** What each row of Sổ tài sản is meant for, and what is counted as already given away. Only shown here: Sổ tài sản and Tháp tài sản do not change. */
export function MoneyPurposes({ refresh, onChanged }: { refresh: number; onChanged?: () => void }) {
  const [view, setView] = useState<PurposesView | null>(null);
  const [name, setName] = useState("");
  const [given, setGiven] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);
  const [bulk, setBulk] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<PurposesView>("money-purposes").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [refresh]);
  async function put(purposes: Purpose[], tags: Record<string, string>): Promise<boolean> {
    if (!view) return false;
    setBusy(true);
    try {
      setView(await api<PurposesView>("money-purposes", { method: "PUT", body: { purposes, tags, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      onChanged?.();
      return true;
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); return false; }
    finally { setBusy(false); }
  }
  const has = (n: string) => view?.data.purposes.some((p) => p.name.toLowerCase() === n.toLowerCase());
  async function add(n: string, isGiven = false): Promise<boolean> {
    if (!view) return false;
    if (!n.trim()) { setMessage("Nhập tên mục đích."); return false; }
    if (has(n.trim())) { setMessage("Đã có mục đích này."); return false; }
    return put([...view.data.purposes, { id: requestId(), name: n.trim().slice(0, 40), given: isGiven }], view.data.tags);
  }
  function remove(p: Purpose) {
    if (!view || !window.confirm(`Xóa mục đích "${p.name}"? Các khoản đã gắn sẽ về Chưa gắn.`)) return;
    void put(view.data.purposes.filter((x) => x.id !== p.id), Object.fromEntries(Object.entries(view.data.tags).filter(([, v]) => v !== p.id)));
  }
  function tagAll(ids: string[], purpose: string, created?: Purpose) {
    if (!view) return;
    const tags = { ...view.data.tags };
    for (const id of ids) { if (purpose) tags[id] = purpose; else delete tags[id]; }
    void put(created ? [...view.data.purposes, created] : view.data.purposes, tags);
  }
  async function tagPicked() {
    if (!view || !picked.length || !bulk) return;
    const ids = picked;
    tagAll(ids, bulk);
    setPicked([]);
  }
  const v = view?.view;
  const purposes = view?.data.purposes ?? [];
  const suggestions = SUGGESTED.filter((s) => !has(s));
  const allPicked = !!view && view.rows.length > 0 && picked.length === view.rows.length;
  return (
    <section className="surface" aria-label="Mục đích từng khoản tiền">
      <h2>Mục đích từng khoản tiền</h2>
      <p className="caption wrap">Gắn mỗi dòng của Sổ tài sản với một mục đích do bạn đặt tên. Mục đích đánh dấu “tính là đã chi” (ví dụ khoản để dành cho con) được trừ khỏi phần là của bạn. Chỉ để xem: Sổ tài sản và Tháp tài sản không thay đổi. Phép tính chỉ gồm các dòng trong Sổ tài sản, không gồm cổ phiếu và tiền trong tài khoản chứng khoán.</p>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void add(name, given).then((ok) => { if (ok) { setName(""); setGiven(false); } }); }}>
        <label className="field">Tên mục đích<input maxLength={40} value={name} disabled={!view || busy} onChange={(e) => setName(e.target.value)} /></label>
        <label className="db-check"><input type="checkbox" checked={given} disabled={!view || busy} onChange={(e) => setGiven(e.target.checked)} /> Xem như đã chi</label>
        <button type="submit" className="btn" disabled={!view || busy}><Plus size={14} aria-hidden="true" />Thêm mục đích</button>
      </form>
      {view && suggestions.length > 0 && <p className="mp-suggest"><span className="caption">Gợi ý, bấm để tạo:</span>
        {suggestions.map((s) => <button key={s} type="button" className="btn" disabled={busy} onClick={() => void add(s)}>+ {s}</button>)}</p>}
      {message && <p className="errors" role="alert">{message}</p>}
      {view && purposes.length === 0 && <p className="notice" data-testid="mp-empty">Chưa có mục đích nào. Tạo bằng ô “Tên mục đích” ở trên, bấm một gợi ý, hoặc chọn “+ Tạo mục đích mới…” trong ô Mục đích của từng dòng bên dưới.</p>}
      {v && v.purposes.length > 0 && <table className="fv-table" aria-label="Tổng theo mục đích">
        <thead><tr><th>Mục đích</th><th>Tính là đã chi</th><th className="num">Số khoản</th><th className="num">Giá trị</th><th /></tr></thead>
        <tbody>
          {v.purposes.map((p) => <tr key={p.id}><td data-label="Mục đích">{p.name}</td>
            <td data-label="Tính là đã chi"><input type="checkbox" aria-label={`Tính là đã chi: ${p.name}`} checked={p.given} disabled={busy}
              onChange={(e) => void put(purposes.map((x) => (x.id === p.id ? { ...x, given: e.target.checked } : x)), view!.data.tags)} /></td>
            <td data-label="Số khoản" className="num">{p.count}</td><td data-label="Giá trị" className="num">{formatVnd(p.total)}</td>
            <td className="db-actions"><button type="button" className="btn" aria-label={`Xóa mục đích ${p.name}`} disabled={busy} onClick={() => remove(p)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td></tr>)}
          <tr><td data-label="Mục đích" className="muted">Chưa gắn</td><td /><td data-label="Số khoản" className="num">{v.unassigned.count}</td><td data-label="Giá trị" className="num">{formatVnd(v.unassigned.total)}</td><td /></tr>
        </tbody>
      </table>}
      {v && <dl className="eb-result">
        <div><dt>Tổng Sổ tài sản</dt><dd>{formatVnd(v.total)}</dd></div>
        <div><dt>Xem như đã chi</dt><dd data-testid="mp-given">{formatVnd(v.given_total)}</dd></div>
        <div className="eb-main"><dt>Còn lại là của bạn</dt><dd data-testid="mp-mine">{formatVnd(v.mine_total)}</dd></div>
      </dl>}
      {view && (view.rows.length === 0 ? <p className="muted">Sổ tài sản chưa có dòng nào.</p> : <>
        <div className="mp-bulk">
          <label className="field">Mục đích cho các khoản đã chọn
            <select value={bulk} disabled={busy || purposes.length === 0} onChange={(e) => setBulk(e.target.value)}><option value="">Chọn mục đích</option>{purposes.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
          <button type="button" className="btn" disabled={busy || !bulk || picked.length === 0} onClick={() => void tagPicked()}><Tags size={14} aria-hidden="true" />Gắn cho {picked.length} khoản</button>
        </div>
        <table className="fv-table" aria-label="Gắn mục đích cho từng khoản">
          <thead><tr><th><input type="checkbox" aria-label="Chọn tất cả" checked={allPicked} onChange={(e) => setPicked(e.target.checked ? view.rows.map((r) => r.id) : [])} /></th><th>Khoản</th><th>Loại</th><th className="num">Giá trị</th><th>Mục đích</th></tr></thead>
          <tbody>{view.rows.map((r) => <tr key={r.id}>
            <td><input type="checkbox" aria-label={`Chọn ${r.name}`} checked={picked.includes(r.id)} onChange={(e) => setPicked((old) => (e.target.checked ? [...old, r.id] : old.filter((x) => x !== r.id)))} /></td>
            <td data-label="Khoản">{r.name}</td><td data-label="Loại">{KIND[r.kind]}</td>
            <td data-label="Giá trị" className="num">{formatVnd(r.value)}{r.at_cost && <div className="caption">theo vốn đã mua</div>}</td>
            <td data-label="Mục đích"><PurposeSelect label={`Mục đích của ${r.name}`} value={view.data.tags[r.id] ?? ""} purposes={purposes} disabled={busy} onPick={(id, created) => tagAll([r.id], id, created)} /></td></tr>)}</tbody>
        </table>
      </>)}
    </section>
  );
}
