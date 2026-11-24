"use client";
import { useEffect, useState } from "react";
import { Plus, Tag, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Basket = { id: string; name: string };
type Stored = { baskets: Basket[]; tags: Record<string, string> };
export type BasketRow = { id: string | null; name: string | null; closed: number; open: number; realised: string; released: string; realised_ratio: string | null;
  win_rate: string | null; mean_days: string | null; enough: boolean; open_cost: string; unrealised: string | null; missing: string[] };
type Period = { key: string; symbol: string; start: string; end: string | null; basket: string | null };
type Data = { version: number; data: Stored; view: { rows: BasketRow[]; periods: Period[]; stale: string[] } };

const SUGGESTED = ["Ngắn hạn", "Dài hạn", "Theo môi giới", "Tự quyết", "Bắt đáy"];
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const signed = (r: string) => `${r.startsWith("-") || !/[1-9]/.test(r) ? "" : "+"}${formatRatio(r, 1)}`;

export function basketResult(r: BasketRow): string {
  const sold = r.realised_ratio === null ? "Chưa bán lần nào" : `Lãi đã chốt ${formatVnd(r.realised)} (${signed(r.realised_ratio)} trên giá vốn đã bán)`;
  if (!r.enough || r.win_rate === null || r.mean_days === null) return `${sold} · chưa đủ 5 đợt đã đóng`;
  return `${sold} · ${formatRatio(r.win_rate, 1)} đợt có lãi · nắm bình quân ${r.mean_days.replace(".", ",")} ngày`;
}

export function basketHeld(r: BasketRow): string {
  if (r.open === 0) return "—";
  const cost = `Giá vốn ${formatVnd(r.open_cost)}`;
  return r.missing.length ? `${cost}; chưa có giá: ${r.missing.join(", ")}` : r.unrealised === null ? cost : `${cost}, lãi chưa chốt ${formatVnd(r.unrealised)}`;
}

/** Giỏ chiến lược: the owner's own baskets of holding periods and what each made. Figures only. */
export function BasketsView() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [target, setTarget] = useState("");
  useEffect(() => { api<Data>("baskets").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function save(next: Stored, done: string) {
    if (!d) return;
    setBusy(true);
    try {
      setD(await api<Data>("baskets", { method: "PUT", body: { ...next, expected_version: d.version, request_id: requestId() } }));
      setMessage(done);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu.");
    } finally { setBusy(false); }
  }
  function add(text: string) {
    if (!d) return;
    const clean = text.trim();
    if (!clean) { setMessage("Nhập tên giỏ."); return; }
    if (d.data.baskets.some((b) => b.name.toLocaleLowerCase("vi") === clean.toLocaleLowerCase("vi"))) { setMessage("Đã có giỏ tên này."); return; }
    void save({ ...d.data, baskets: [...d.data.baskets, { id: requestId(), name: clean }] }, `Đã tạo giỏ «${clean}».`).then(() => setName(""));
  }
  function remove(id: string) {
    if (!d) return;
    const tags = Object.fromEntries(Object.entries(d.data.tags).filter(([, v]) => v !== id));
    void save({ baskets: d.data.baskets.filter((b) => b.id !== id), tags }, "Đã xóa giỏ; các đợt của giỏ về Chưa gắn giỏ.");
  }
  function tag(keys: string[], basket: string) {
    if (!d || keys.length === 0) return;
    const tags = { ...d.data.tags };
    for (const k of keys) { if (basket) tags[k] = basket; else delete tags[k]; }
    void save({ ...d.data, tags }, keys.length > 1 ? `Đã gắn ${keys.length} đợt.` : "Đã gắn giỏ.").then(() => setPicked(new Set()));
  }
  const names = new Map((d?.data.baskets ?? []).map((b) => [b.id, b.name]));
  const toggle = (k: string) => setPicked((s) => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n; });
  return (
    <section className="surface" aria-label="Giỏ chiến lược">
      <h2>Giỏ chiến lược</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!d && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {d && <>
        <p className="caption">Tự đặt các giỏ theo cách đánh (ví dụ ngắn hạn, dài hạn, theo môi giới) rồi gắn từng đợt nắm vào một giỏ, để so cách nào thật sự
          hiệu quả với chính bạn. Một đợt là từ lúc mua mã đó khi đang không có cổ phiếu nào đến lúc bán hết. Lãi đã chốt lấy đúng số của sổ (giá vốn bình
          quân), chưa gồm cổ tức tiền. Chỉ là số đã xảy ra, không phải khuyến nghị.</p>
        <div className="actions">
          {d.data.baskets.map((b) => <span key={b.id} className="pill">{b.name}
            <button className="btn" aria-label={`Xóa giỏ ${b.name}`} disabled={busy} onClick={() => remove(b.id)}><Trash2 size={14} aria-hidden="true" /></button></span>)}
        </div>
        {d.data.baskets.length < 8 && <>
          <div className="formgrid"><label className="field">Tên giỏ mới<input value={name} maxLength={40} disabled={busy} onChange={(e) => setName(e.target.value)} /></label></div>
          <div className="actions"><button className="btn primary" disabled={busy} onClick={() => add(name)}><Plus size={16} aria-hidden="true" />Tạo giỏ</button>
            {SUGGESTED.filter((s) => !d.data.baskets.some((b) => b.name === s)).map((s) =>
              <button key={s} className="btn" disabled={busy} onClick={() => add(s)}>+ {s}</button>)}</div>
        </>}
        {d.view.stale.length > 0 && <p className="caption" role="status">{d.view.stale.length} nhãn không còn khớp đợt nào (sổ đã sửa ngày mua): {d.view.stale.join(", ")}. Gắn lại ở bảng dưới.</p>}

        <h3>Kết quả theo giỏ</h3>
        <div className="tablewrap"><table className="fv-table cc-table" aria-label="Kết quả theo giỏ">
          <thead><tr><th>Giỏ</th><th className="num">Đợt đã đóng / đang nắm</th><th>Đã chốt</th><th>Đang nắm</th></tr></thead>
          <tbody>{d.view.rows.map((r) => <tr key={r.id ?? "none"}>
            <td data-label="Giỏ"><strong>{r.name ?? "Chưa gắn giỏ"}</strong></td>
            <td data-label="Đợt đã đóng / đang nắm" className="num">{r.closed} / {r.open}</td>
            <td data-label="Đã chốt">{basketResult(r)}</td>
            <td data-label="Đang nắm">{basketHeld(r)}</td>
          </tr>)}</tbody>
        </table></div>

        <h3>Các đợt nắm</h3>
        {d.view.periods.length === 0 ? <p className="muted">Chưa có lệnh mua trong sổ.</p> : <>
          {d.data.baskets.length > 0 && <div className="formgrid">
            <label className="field">Gắn các đợt đã chọn vào<select value={target} disabled={busy} onChange={(e) => setTarget(e.target.value)}>
              <option value="">Chưa gắn giỏ</option>{d.data.baskets.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
            <div className="actions"><button className="btn" disabled={busy || picked.size === 0} onClick={() => tag([...picked], target)}>
              <Tag size={16} aria-hidden="true" />Gắn {picked.size} đợt</button></div></div>}
          <div className="tablewrap"><table className="fv-table cc-table" aria-label="Các đợt nắm">
            <thead><tr><th /><th>Mã</th><th>Đợt</th><th>Giỏ</th></tr></thead>
            <tbody>{[...d.view.periods].reverse().map((p) => <tr key={p.key}>
              <td><input type="checkbox" aria-label={`Chọn đợt ${p.symbol} từ ${day(p.start)}`} checked={picked.has(p.key)} onChange={() => toggle(p.key)} /></td>
              <td data-label="Mã"><strong>{p.symbol}</strong></td>
              <td data-label="Đợt">{day(p.start)} → {p.end ? day(p.end) : "đang nắm"}</td>
              <td data-label="Giỏ">{d.data.baskets.length === 0 ? <span className="muted">tạo giỏ trước</span>
                : <select aria-label={`Giỏ của ${p.symbol} từ ${day(p.start)}`} value={p.basket ?? ""} disabled={busy} onChange={(e) => tag([p.key], e.target.value)}>
                  <option value="">Chưa gắn giỏ</option>{d.data.baskets.map((b) => <option key={b.id} value={b.id}>{names.get(b.id)}</option>)}</select>}</td>
            </tr>)}</tbody>
          </table></div>
        </>}
        {message && <p className="caption" role="status">{message}</p>}
      </>}
    </section>
  );
}
