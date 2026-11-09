"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd } from "../lib/format";

type Purpose = { id: string; name: string; given: boolean };
type Row = { id: string; kind: "account" | "deposit" | "bond" | "gold" | "crypto"; name: string; value: string; at_cost: boolean };
type Total = Purpose & { total: string; count: number };
type View = { version: number; data: { purposes: Purpose[]; tags: Record<string, string> }; rows: Row[];
  view: { purposes: Total[]; unassigned: { total: string; count: number }; total: string; given_total: string; mine_total: string } };

const KIND: Record<Row["kind"], string> = { account: "Tiền mặt", deposit: "Sổ tiền gửi", bond: "Trái phiếu, quỹ", gold: "Vàng", crypto: "Tiền số" };

/** What each row of Sổ tài sản is meant for, and what is counted as already given away. Only shown here: Sổ tài sản and Tháp tài sản do not change. */
export function MoneyPurposes({ refresh }: { refresh: number }) {
  const [view, setView] = useState<View | null>(null);
  const [name, setName] = useState("");
  const [given, setGiven] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("money-purposes").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [refresh]);
  async function put(purposes: Purpose[], tags: Record<string, string>): Promise<boolean> {
    if (!view) return false;
    setBusy(true);
    try {
      setView(await api<View>("money-purposes", { method: "PUT", body: { purposes, tags, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      return true;
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); return false; }
    finally { setBusy(false); }
  }
  async function add() {
    if (!view) return;
    if (!name.trim()) { setMessage("Nhập tên mục đích."); return; }
    if (await put([...view.data.purposes, { id: requestId(), name: name.trim(), given }], view.data.tags)) { setName(""); setGiven(false); }
  }
  function remove(p: Purpose) {
    if (!view || !window.confirm(`Xóa mục đích "${p.name}"? Các khoản đã gắn sẽ về Chưa gắn.`)) return;
    void put(view.data.purposes.filter((x) => x.id !== p.id), Object.fromEntries(Object.entries(view.data.tags).filter(([, v]) => v !== p.id)));
  }
  function tag(id: string, purpose: string) {
    if (!view) return;
    const { [id]: _old, ...rest } = view.data.tags;
    void put(view.data.purposes, purpose ? { ...rest, [id]: purpose } : rest);
  }
  const v = view?.view;
  return (
    <section className="surface" aria-label="Mục đích từng khoản tiền">
      <h2>Mục đích từng khoản tiền</h2>
      <p className="caption wrap">Gắn mỗi dòng của Sổ tài sản với một mục đích do bạn đặt tên, ví dụ quỹ mua nhà. Mục đích đánh dấu “xem như đã chi” (ví dụ khoản để dành cho con) được trừ khỏi phần là của bạn. Chỉ để xem: Sổ tài sản và Tháp tài sản không thay đổi. Phép tính chỉ gồm các dòng trong Sổ tài sản, không gồm cổ phiếu và tiền trong tài khoản chứng khoán.</p>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void add(); }}>
        <label className="field">Tên mục đích<input maxLength={40} value={name} disabled={!view || busy} onChange={(e) => setName(e.target.value)} /></label>
        <label className="db-check"><input type="checkbox" checked={given} disabled={!view || busy} onChange={(e) => setGiven(e.target.checked)} /> Xem như đã chi</label>
        <button type="submit" className="btn" disabled={!view || busy}><Plus size={14} aria-hidden="true" />Thêm mục đích</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {v && v.purposes.length > 0 && <table className="fv-table" aria-label="Tổng theo mục đích">
        <thead><tr><th>Mục đích</th><th className="num">Số khoản</th><th className="num">Giá trị</th><th /></tr></thead>
        <tbody>
          {v.purposes.map((p) => <tr key={p.id}><td data-label="Mục đích">{p.name}{p.given && <span className="pill warn">xem như đã chi</span>}</td><td data-label="Số khoản" className="num">{p.count}</td><td data-label="Giá trị" className="num">{formatVnd(p.total)}</td>
            <td className="db-actions"><button type="button" className="btn" aria-label={`Xóa mục đích ${p.name}`} disabled={busy} onClick={() => remove(p)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td></tr>)}
          <tr><td data-label="Mục đích" className="muted">Chưa gắn</td><td data-label="Số khoản" className="num">{v.unassigned.count}</td><td data-label="Giá trị" className="num">{formatVnd(v.unassigned.total)}</td><td /></tr>
        </tbody>
      </table>}
      {v && <dl className="eb-result">
        <div><dt>Tổng Sổ tài sản</dt><dd>{formatVnd(v.total)}</dd></div>
        <div><dt>Xem như đã chi</dt><dd data-testid="mp-given">{formatVnd(v.given_total)}</dd></div>
        <div className="eb-main"><dt>Còn lại là của bạn</dt><dd data-testid="mp-mine">{formatVnd(v.mine_total)}</dd></div>
      </dl>}
      {view && (view.rows.length === 0 ? <p className="muted">Sổ tài sản chưa có dòng nào.</p> : <table className="fv-table" aria-label="Gắn mục đích cho từng khoản">
        <thead><tr><th>Khoản</th><th>Loại</th><th className="num">Giá trị</th><th>Mục đích</th></tr></thead>
        <tbody>{view.rows.map((r) => <tr key={r.id}><td data-label="Khoản">{r.name}</td><td data-label="Loại">{KIND[r.kind]}</td>
          <td data-label="Giá trị" className="num">{formatVnd(r.value)}{r.at_cost && <div className="caption">theo vốn đã mua</div>}</td>
          <td data-label="Mục đích"><select aria-label={`Mục đích của ${r.name}`} value={view.data.tags[r.id] ?? ""} disabled={busy} onChange={(e) => tag(r.id, e.target.value)}>
            <option value="">Chưa gắn</option>{view.data.purposes.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></td></tr>)}</tbody>
      </table>)}
    </section>
  );
}
