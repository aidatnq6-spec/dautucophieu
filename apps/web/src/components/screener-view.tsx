"use client";
import { useCallback, useEffect, useState } from "react";
import { Save, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";

type Value = string | string[] | null;
type Row = { symbol: string; values: Record<string, Value>; missing: Record<string, string>; foreign20_bn?: string | null };
type Criterion = { label: string; values: Record<string, string> };
type Screen = { id: string; name: string; criteria: Record<string, string[]>; notify: boolean };
type Data = { version: number; screens: Screen[]; rows: Row[]; criteria: Record<string, Criterion>; as_of: { trend: string | null; foreign: string | null } };

/** The server's rule: "or" within a criterion, "and" between criteria; a ticker without data for a criterion in use never matches. */
export function matches(criteria: Record<string, string[]>, row: { values: Record<string, Value> }): { ok: boolean; lacking: string[] } {
  const lacking: string[] = [];
  let ok = true;
  for (const [key, wanted] of Object.entries(criteria)) {
    const value = row.values[key];
    if (value === null || value === undefined) { lacking.push(key); ok = false; continue; }
    if (!(Array.isArray(value) ? value.some((v) => wanted.includes(v)) : wanted.includes(value))) ok = false;
  }
  return { ok, lacking };
}

/** The screen just saved: the id that was not there before (a new screen may share another's name), else the one being edited. */
export function savedScreenId(before: { id: string }[], after: { id: string }[], editing: string | null): string | null {
  const known = new Set(before.map((s) => s.id));
  return after.find((s) => !known.has(s.id))?.id ?? editing;
}

const same = (a: Record<string, string[]>, b: Record<string, string[]>) =>
  JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
const dmy = (iso: string | null) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "chưa có");

/** Bộ lọc tín hiệu: the watched tickers narrowed by several stored signals at once, saved as screens. */
export function ScreenerView() {
  const [data, setData] = useState<Data | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [criteria, setCriteria] = useState<Record<string, string[]>>({ verdict: ["cheap"] });
  const [loaded, setLoaded] = useState<Screen | null>(null);
  const [name, setName] = useState("");
  const [notify, setNotify] = useState(false);
  const load = useCallback(() => api<Data>("screener").then(setData, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải bộ lọc.")), []);
  useEffect(() => { void load(); }, [load]);

  async function change(body: Record<string, unknown>) {
    if (!data) return;
    try {
      const next = await api<Data>("screener", { method: "PUT", body: { ...body, expected_version: data.version, request_id: requestId() } });
      setData(next);
      setMessage(null);
      return next;
    } catch (e) {
      if (e instanceof ApiError && e.failure.code === "version_conflict") {  // saved elsewhere meanwhile: reload, keep the choices
        await load();
        setMessage("Bộ lọc vừa được cập nhật ở nơi khác nên đã tải lại; hãy bấm lưu lần nữa.");
        return;
      }
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu bộ lọc.");
    }
  }
  const toggle = (key: string, value: string) => setCriteria((c) => {
    const now = c[key] ?? [];
    const next = now.includes(value) ? now.filter((v) => v !== value) : [...now, value];
    const rest = Object.fromEntries(Object.entries(c).filter(([k]) => k !== key));
    return next.length ? { ...rest, [key]: next } : rest;
  });
  const open = (s: Screen) => { setLoaded(s); setCriteria(s.criteria); setName(s.name); setNotify(s.notify); };
  const show = (key: string, v: Value) => (v === null || v === undefined ? "—" : Array.isArray(v) ? v.map((x) => data?.criteria[key].values[x] ?? x).join(", ")
    : data?.criteria[key].values[v] ?? v);
  const results = data ? data.rows.map((r) => ({ row: r, ...matches(criteria, r) })) : [];
  const found = results.filter((r) => r.ok);
  const lacking = results.filter((r) => !r.ok && r.lacking.length);
  const keys = Object.keys(criteria);
  return (
    <section className="surface" aria-label="Bộ lọc tín hiệu">
      <h2>Bộ lọc tín hiệu</h2>
      <p className="caption">Thu hẹp các mã theo dõi bằng nhiều tín hiệu đã có: trong một tiêu chí chọn nhiều giá trị là “hoặc”, giữa các tiêu chí là “và”.
        Mã thiếu dữ liệu cho tiêu chí đang dùng không được tính là khớp. Định giá và chất lượng theo trang Định giá; MACD, RSI theo bảng Xu hướng
        (lập sau 15:30); khối ngoại cộng 20 phiên đã lưu. Chỉ để thu hẹp danh sách; phần mềm không khuyên mua hay bán.</p>
      {message && <p className="errors" role="alert">{message}</p>}
      {!data && !message && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {data && <>
        <p className="caption" data-testid="screen-dates">Bảng Xu hướng phiên {dmy(data.as_of.trend)} · khối ngoại đã lưu tới phiên {dmy(data.as_of.foreign)}.</p>
        {data.screens.length > 0 && <div className="sc-saved" role="group" aria-label="Bộ lọc đã lưu">
          {data.screens.map((s) => <button key={s.id} type="button" className={`btn ${loaded?.id === s.id && same(s.criteria, criteria) ? "primary" : ""}`}
            onClick={() => open(s)}>
            {s.name}{s.notify ? " · nhắn" : ""}</button>)}
        </div>}
        <div className="sc-criteria">
          {Object.entries(data.criteria).map(([key, c]) => <fieldset key={key}><legend>{c.label}</legend>
            {Object.entries(c.values).map(([v, label]) => <label key={v} className="th-check">
              <input type="checkbox" checked={(criteria[key] ?? []).includes(v)} onChange={() => toggle(key, v)} />{label}</label>)}
          </fieldset>)}
        </div>
        <p role="status" data-testid="screen-count"><strong>{found.length} mã khớp</strong>{lacking.length > 0 && ` · ${lacking.length} mã thiếu dữ liệu cho tiêu chí đang dùng`}</p>
        {found.length > 0 && <div className="tablewrap"><table aria-label="Kết quả bộ lọc">
          <thead><tr><th>Mã</th>{keys.map((k) => <th key={k}>{data.criteria[k].label}</th>)}</tr></thead>
          <tbody>{found.map(({ row }) => <tr key={row.symbol}><td><strong>{row.symbol}</strong></td>
            {keys.map((k) => <td key={k}>{show(k, row.values[k])}{k === "foreign20" && row.foreign20_bn ? ` (${Number(row.foreign20_bn).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} tỷ)` : ""}</td>)}</tr>)}</tbody>
        </table></div>}
        {lacking.length > 0 && <details><summary className="caption">Mã thiếu dữ liệu ({lacking.length})</summary>
          <ul className="sc-missing">{lacking.map(({ row, lacking: miss }) => <li key={row.symbol}><strong>{row.symbol}</strong>:{" "}
            {miss.map((k) => `${data.criteria[k].label} — ${row.missing[k] ?? "thiếu"}`).join("; ")}</li>)}</ul>
        </details>}
        <form className="sc-save" aria-label="Lưu bộ lọc" onSubmit={(e) => {
          e.preventDefault();
          const before = data.screens;
          void change({ action: "save", screen: { id: loaded?.id, name, criteria, notify } }).then((next) => {
            if (!next) return;  // failed: keep the form as it is
            const id = savedScreenId(before, next.screens, loaded?.id ?? null);
            setLoaded(next.screens.find((s) => s.id === id) ?? null);
          });
        }}>
          <label className="field">Tên bộ lọc<input value={name} maxLength={60} onChange={(e) => setName(e.target.value)} placeholder="Rẻ và mạnh" /></label>
          <label className="th-check"><input type="checkbox" checked={notify} onChange={(e) => setNotify(e.target.checked)} />Nhắn Telegram khi có mã mới lọt vào (sau giờ đóng cửa)</label>
          <button className="btn primary" type="submit" disabled={!name.trim() || keys.length === 0}><Save size={15} aria-hidden="true" />{loaded ? "Lưu thay đổi" : "Lưu bộ lọc"}</button>
          {loaded && <button className="btn" type="button" onClick={() => { if (window.confirm(`Xóa bộ lọc “${loaded.name}”?`)) void change({ action: "delete", id: loaded.id })
            .then((next) => { if (next) { setLoaded(null); setName(""); setNotify(false); } }); }}><Trash2 size={15} aria-hidden="true" />Xóa</button>}
          {loaded && <button className="btn" type="button" onClick={() => { setLoaded(null); setName(""); setNotify(false); }}>Bộ lọc mới</button>}
        </form>
      </>}
    </section>
  );
}
