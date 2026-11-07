"use client";
import { type FormEvent, useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";

type Row = { period: string; values: Record<string, string>; total: string | null; shares: Record<string, string>; total_yoy: string | null;
  source: string | null; missing: string[] };
type Group = { id: string; name: string; unit: string; period: "month" | "quarter" | "year"; series: string[]; chart: "stack" | "line"; periods: string[]; rows: Row[] };
type View = { symbol: string; version: number; groups: Group[] };

type Candidate = { value: string; page: number; text: string };
export type Proposal = { url: string; values: Record<string, Candidate[]>; missing: string[]; warnings: string[] };

/** The first candidate of each line, and the link with the pages they came from as the source. */
export function applyProposal(p: Proposal): { values: Record<string, string>; source: string } {
  const values: Record<string, string> = {};
  const pages = new Set<number>();
  for (const [s, list] of Object.entries(p.values)) {
    if (list[0]) { values[s] = list[0].value; pages.add(list[0].page); }
  }
  return { values, source: pages.size ? `${p.url} (trang ${[...pages].sort((a, b) => a - b).join(", ")})` : p.url };
}

const COLORS = ["#1f2a5c", "#3b82f6", "#15803d", "#a16207", "#7c3aed", "#b14249", "#0891b2", "#57534e"];
const KIND: Record<Group["period"], [string, string]> = { month: ["tháng", "2026-09"], quarter: ["quý", "2026-Q3"], year: ["năm", "2026"] };
const SHOWN = 12;

export function slugify(name: string): string {
  return name.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[đĐ]/g, "d").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
}

export function parseSeries(text: string): string[] {
  return text.split(",").map((s) => s.trim()).filter(Boolean);
}

/** The value the chart's height is scaled to: the largest total (stacked) or the largest single value (lines). */
export function stackTop(rows: { values: Record<string, string>; total: string | null }[], chart: "stack" | "line"): number {
  const values = rows.flatMap((r) => (chart === "stack" ? [r.total ?? Object.values(r.values).reduce((a, v) => String(Number(a) + Number(v)), "0")] : Object.values(r.values)));
  return values.length ? Math.max(...values.map(Number)) : 0;
}

const num = (v: string | number) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 2 });
const pct = (v: string) => `${Number(v) > 0 ? "+" : ""}${(Number(v) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
const label = (p: string) => (p.includes("-Q") ? `Q${p.slice(-1)}/${p.slice(2, 4)}` : p.length === 7 ? `${p.slice(5)}/${p.slice(2, 4)}` : p);

function Chart({ g }: { g: Group }) {
  const rows = g.rows.slice(-SHOWN);
  const top = stackTop(rows, g.chart) * 1.1 || 1;
  const W = 640, H = 220, L = 48, B = 24, T = 10;
  const step = (W - L - 8) / Math.max(rows.length, 1);
  const y = (v: number) => T + (1 - v / top) * (H - T - B);
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${g.name} (${g.unit})`} className="op-chart">
      {[0, 0.5, 1].map((f) => <g key={f}><line x1={L} x2={W - 8} y1={y(top * f)} y2={y(top * f)} className="mc-grid" />
        <text x={L - 6} y={y(top * f) + 4} className="mc-axis" textAnchor="end">{num(Math.round(top * f))}</text></g>)}
      {rows.map((r, i) => <text key={r.period} x={L + step * (i + 0.5)} y={H - 6} className="mc-axis" textAnchor="middle">{label(r.period)}</text>)}
      {g.chart === "stack" ? rows.map((r, i) => {
        let base = 0;
        return <g key={r.period}>{g.series.map((s, k) => {
          const v = Number(r.values[s] ?? 0);
          const rect = <rect key={s} x={L + step * i + step * 0.18} width={step * 0.64} y={y(base + v)} height={Math.max(0, y(base) - y(base + v))} fill={COLORS[k % COLORS.length]} />;
          base += v;
          return rect;
        })}</g>;
      }) : g.series.map((s, k) => {
        const pts = rows.map((r, i) => (r.values[s] === undefined ? null : `${L + step * (i + 0.5)},${y(Number(r.values[s]))}`)).filter(Boolean);
        return <polyline key={s} points={pts.join(" ")} fill="none" stroke={COLORS[k % COLORS.length]} strokeWidth={2} />;
      })}
    </svg>
  );
}

function GroupBlock({ g, symbol, version, onView, onError }: { g: Group; symbol: string; version: number; onView: (v: View) => void; onError: (m: string) => void }) {
  const [period, setPeriod] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [source, setSource] = useState("");
  const [pdf, setPdf] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [reading, setReading] = useState(false);
  const read = async () => {
    setReading(true);
    try {
      const p = await api<Proposal>(`operating/${encodeURIComponent(symbol)}/groups/${g.id}/read-pdf`, { method: "POST", body: { url: pdf.trim(), request_id: requestId() } });
      const filled = applyProposal(p);
      setProposal(p);
      setValues(filled.values);
      setSource(filled.source);
    } catch (err) {
      onError(err instanceof ApiError ? err.failure.message : "Không đọc được PDF.");
    } finally {
      setReading(false);
    }
  };
  const call = async (path: string, method: "PUT" | "POST", body: object) => {
    try {
      onView(await api<View>(`operating/${encodeURIComponent(symbol)}/groups/${g.id}${path}`, { method, body: { ...body, expected_version: version, request_id: requestId() } }));
      return true;
    } catch (err) {
      onError(err instanceof ApiError ? err.failure.message : "Không lưu được.");
      return false;
    }
  };
  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (await call(`/values/${period.trim()}`, "PUT", { values, source })) { setValues({}); setPeriod(""); setProposal(null); }
  };
  const rows = g.rows.slice(-SHOWN);
  return (
    <div className="op-group" role="group" aria-label={g.name}>
      <h3>{g.name} <span className="caption">— {g.unit} · theo {KIND[g.period][0]} · {g.chart === "stack" ? "cột chồng" : "đường"}</span></h3>
      {rows.length > 0 ? <>
        <Chart g={g} />
        <p className="pb-legend">{g.series.map((s, k) => <span key={s}><i style={{ background: COLORS[k % COLORS.length] }} />{s}</span>)}</p>
        <div className="pb-scroll"><table className="pb-table">
          <thead><tr><th>Kỳ</th>{g.series.map((s) => <th key={s} className="num">{s}</th>)}{g.chart === "stack" && <><th className="num">Tổng</th><th className="num">So cùng kỳ</th></>}
            <th>Nguồn</th><th /></tr></thead>
          <tbody>{[...rows].reverse().map((r) => <tr key={r.period}><td>{label(r.period)}</td>
            {g.series.map((s) => <td key={s} className="num">{r.values[s] !== undefined ? num(r.values[s]) : "—"}
              {r.shares[s] && <span className="caption"> ({(Number(r.shares[s]) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%)</span>}</td>)}
            {g.chart === "stack" && <><td className="num">{r.total !== null ? num(r.total) : `thiếu ${r.missing.join(", ")}`}</td>
              <td className={`num ${r.total_yoy && Number(r.total_yoy) < 0 ? "negative" : "positive"}`}>{r.total_yoy ? pct(r.total_yoy) : "—"}</td></>}
            <td className="caption">{r.source}</td>
            <td><button type="button" className="btn" aria-label={`Xóa ${g.name} ${r.period}`} onClick={() => call(`/values/${r.period}/delete`, "POST", {})}>Xóa</button></td></tr>)}</tbody>
        </table></div>
      </> : <p className="muted">Chưa có kỳ nào.</p>}
      <div className="ap-form" role="group" aria-label={`Đọc ${g.name} từ PDF`}>
        <label className="field ap-source"><span>Đọc từ PDF công khai (link https)</span>
          <input value={pdf} onChange={(e) => setPdf(e.target.value)} placeholder="https://…/ban-tin-san-xuat-kinh-doanh.pdf" /></label>
        <button type="button" className="btn" disabled={reading || !pdf.trim()} onClick={read}>{reading ? "Đang đọc…" : "Đọc PDF"}</button>
      </div>
      {proposal && <div className="op-proposal" role="region" aria-label={`Số đề xuất từ PDF cho ${g.name}`}>
        <p className="caption wrap">Số đề xuất từ PDF, chưa lưu: kiểm tra từng số và đơn vị (PDF có thể ghi tấn khi nhóm là nghìn tấn), nhập Kỳ rồi bấm Lưu kỳ.
          {proposal.missing.length > 0 && ` Không thấy: ${proposal.missing.join(", ")}.`}{proposal.warnings.map((w) => ` ${w}`)}</p>
        <ul className="ft-checks">{Object.entries(proposal.values).map(([s, list]) => <li key={s}><strong>{s}</strong>:{" "}
          {list.map((c, k) => <button key={k} type="button" className={`btn ${values[s] === c.value ? "primary" : ""}`} aria-pressed={values[s] === c.value}
            title={c.text} onClick={() => setValues({ ...values, [s]: c.value })}>{num(c.value)} · trang {c.page}</button>)}
          <span className="caption"> “{list.find((c) => c.value === values[s])?.text ?? list[0].text}”</span></li>)}</ul>
      </div>}
      <form className="ap-form" onSubmit={save} aria-label={`Nhập ${g.name}`}>
        <label className="field"><span>Kỳ (ví dụ {KIND[g.period][1]})</span><input value={period} onChange={(e) => setPeriod(e.target.value)} /></label>
        {g.series.map((s) => <label key={s} className="field"><span>{s} ({g.unit})</span>
          <input value={values[s] ?? ""} onChange={(e) => setValues({ ...values, [s]: e.target.value })} inputMode="decimal" /></label>)}
        <label className="field ap-source"><span>Nguồn (bắt buộc)</span><input value={source} onChange={(e) => setSource(e.target.value)} placeholder="Bản tin SXKD tháng 10/2026" /></label>
        <button type="submit" className="btn primary">Lưu kỳ</button>
        <button type="button" className="btn" onClick={() => call("/delete", "POST", {})}>Xóa nhóm</button>
      </form>
    </div>
  );
}

export function OperatingFigures({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", unit: "", period: "quarter", series: "", chart: "stack" });
  useEffect(() => {
    api<View>(`operating/${encodeURIComponent(symbol)}`).then(setView, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (!view) return error ? <p className="errors" role="alert">{error}</p> : <p className="muted fx-loading" role="status">Đang tải số liệu vận hành…</p>;
  const create = async (e: FormEvent) => {
    e.preventDefault();
    const id = slugify(draft.name);
    try {
      setView(await api<View>(`operating/${encodeURIComponent(symbol)}/groups/${id || "nhom"}`, { method: "PUT",
        body: { name: draft.name, unit: draft.unit, period: draft.period, series: parseSeries(draft.series), chart: draft.chart,
          expected_version: view.version, request_id: requestId() } }));
      setDraft({ name: "", unit: "", period: "quarter", series: "", chart: "stack" });
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.failure.message : "Không lưu được.");
    }
  };
  return (
    <div className="op">
      {view.groups.map((g) => <GroupBlock key={g.id} g={g} symbol={symbol} version={view.version} onView={(v) => { setView(v); setError(null); }} onError={setError} />)}
      {error && <p className="errors" role="alert">{error}</p>}
      <details className="mc-table" open={view.groups.length === 0}>
        <summary>Thêm nhóm số liệu</summary>
        <form className="ap-form" onSubmit={create} aria-label="Thêm nhóm số liệu vận hành">
          <label className="field ap-source"><span>Tên nhóm</span><input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="Sản lượng bán theo sản phẩm" /></label>
          <label className="field"><span>Đơn vị</span><input value={draft.unit} onChange={(e) => setDraft({ ...draft, unit: e.target.value })} placeholder="nghìn tấn" /></label>
          <label className="field"><span>Kỳ</span><select value={draft.period} onChange={(e) => setDraft({ ...draft, period: e.target.value })}>
            <option value="month">Tháng</option><option value="quarter">Quý</option><option value="year">Năm</option></select></label>
          <label className="field ap-source"><span>Các dòng (cách nhau dấu phẩy)</span><input value={draft.series} onChange={(e) => setDraft({ ...draft, series: e.target.value })}
            placeholder="Thép XD, HRC, Ống thép, Tôn mạ" /></label>
          <label className="field"><span>Biểu đồ</span><select value={draft.chart} onChange={(e) => setDraft({ ...draft, chart: e.target.value })}>
            <option value="stack">Cột chồng (cộng thành tổng)</option><option value="line">Đường (không cộng, ví dụ thị phần %)</option></select></label>
          <button type="submit" className="btn primary">Thêm nhóm</button>
        </form>
        <p className="caption wrap">Muốn đọc số từ PDF bản tin: tạo nhóm trước, đặt tên các dòng đúng như chữ trong bản tin (ví dụ “Thép xây dựng”, không viết tắt
          “Thép XD”); ô “Đọc từ PDF công khai” sẽ hiện trong nhóm vừa tạo.</p>
      </details>
      <p className="caption wrap">Số liệu bạn nhập từ bản tin sản xuất kinh doanh, thuyết minh báo cáo tài chính hoặc báo cáo ngành công khai, mỗi kỳ ghi nguồn; lưu trong
        kho cá nhân. Cột chồng cộng các dòng thành tổng, tỷ trọng và % so cùng kỳ; kỳ thiếu một dòng thì không có tổng. Biểu đồ đường giữ nguyên số đã nhập.</p>
    </div>
  );
}
