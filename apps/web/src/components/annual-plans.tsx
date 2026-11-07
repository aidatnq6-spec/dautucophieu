"use client";
import { type FormEvent, useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";

type Line = { actual: string | null; plan: string; ratio: string | null; reason: string | null };
export type Plan = { year: string; source: string; profit_kind: string; profit_label: string; plan_revenue: string | null; plan_profit: string | null;
  through: string | null; revenue: Line | null; profit: Line | null };
type View = { symbol: string; version: number; plans: Plan[] };

const KINDS: [string, string][] = [["npat", "LNST hợp nhất"], ["npat_parent", "LNST công ty mẹ"], ["pbt", "LNTT"]];
const ty = (v: string) => (Math.round(Number(v) / 1e9) || 0).toLocaleString("vi-VN");
const quarter = (p: string) => `Q${p.slice(-1)}/${p.slice(0, 4)}`;

/** The card for one line of a year's plan: year-to-date against the plan; null when the plan has no figure for that line. */
export function planCard(p: Plan, which: "revenue" | "profit"): { title: string; value: string; note: string } | null {
  const line = p[which];
  if (!line) return null;
  const name = which === "revenue" ? "DT" : p.profit_label;
  if (line.actual === null) return { title: `${name} ${p.year} · % kế hoạch`, value: "—", note: `${line.reason ?? "Chưa có số"} · KH ${ty(line.plan)} tỷ` };
  const pct = line.ratio === null ? "—" : `${(Number(line.ratio) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
  return { title: `${name} lũy kế ${p.through ? quarter(p.through) : p.year} · % kế hoạch`, value: pct,
    note: `${ty(line.actual)} / KH ${ty(line.plan)} tỷ${line.reason ? ` · ${line.reason}` : ""}` };
}

export function AnnualPlans({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ year: String(new Date().getFullYear()), revenue: "", profit: "", kind: "npat", source: "" });
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api<View>(`annual-plans/${encodeURIComponent(symbol)}`).then(setView, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (!view) return error ? <p className="errors" role="alert">{error}</p> : null;
  const latest = view.plans[0];
  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      setView(await api<View>(`annual-plans/${encodeURIComponent(symbol)}/${form.year.trim()}`, { method: "PUT",
        body: { revenue: form.revenue, profit: form.profit, profit_kind: form.kind, source: form.source, expected_version: view.version, request_id: requestId() } }));
      setError(null);
      setForm((f) => ({ ...f, revenue: "", profit: "", source: "" }));
    } catch (err) {
      setError(err instanceof ApiError ? err.failure.message : "Không lưu được.");
    } finally {
      setBusy(false);
    }
  };
  const remove = async (year: string) => {
    try {
      setView(await api<View>(`annual-plans/${encodeURIComponent(symbol)}/${year}/delete`, { method: "POST",
        body: { expected_version: view.version, request_id: requestId() } }));
    } catch (err) {
      setError(err instanceof ApiError ? err.failure.message : "Không xóa được.");
    }
  };
  return (
    <div className="ap" aria-label="Kế hoạch năm">
      {latest && <div className="pb-cards">
        {(["revenue", "profit"] as const).map((w) => planCard(latest, w)).filter((c) => c !== null).map((c) =>
          <div key={c!.title}><span className="caption">{c!.title}</span><strong>{c!.value}</strong><span className="caption">{c!.note}</span></div>)}
      </div>}
      <details className="mc-table">
        <summary>Kế hoạch năm (ĐHCĐ){view.plans.length ? ` · ${view.plans.length} năm đã nhập` : " · chưa nhập"}</summary>
        {view.plans.length > 0 && <ul className="ft-checks">{view.plans.map((p) => <li key={p.year}>
          {p.year}: {p.plan_revenue ? `doanh thu ${Number(p.plan_revenue).toLocaleString("vi-VN")} tỷ` : ""}
          {p.plan_revenue && p.plan_profit ? ", " : ""}{p.plan_profit ? `${p.profit_label} ${Number(p.plan_profit).toLocaleString("vi-VN")} tỷ` : ""} · nguồn: {p.source}{" "}
          <button type="button" className="btn" onClick={() => remove(p.year)} aria-label={`Xóa kế hoạch ${p.year}`}>Xóa</button></li>)}</ul>}
        <form className="ap-form" onSubmit={save} aria-label="Nhập kế hoạch năm">
          <label className="field"><span>Năm</span><input value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} inputMode="numeric" /></label>
          <label className="field"><span>Doanh thu (tỷ đồng)</span><input value={form.revenue} onChange={(e) => setForm({ ...form, revenue: e.target.value })} inputMode="decimal" /></label>
          <label className="field"><span>Lợi nhuận (tỷ đồng)</span><input value={form.profit} onChange={(e) => setForm({ ...form, profit: e.target.value })} inputMode="decimal" /></label>
          <label className="field"><span>Loại lợi nhuận</span><select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            {KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
          <label className="field ap-source"><span>Nguồn (bắt buộc)</span><input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}
            placeholder="Nghị quyết ĐHCĐ 2026, ngày họp" /></label>
          <button type="submit" className="btn primary" disabled={busy}>Lưu kế hoạch</button>
        </form>
        {error && <p className="errors" role="alert">{error}</p>}
        <p className="caption wrap">Số kế hoạch bạn nhập từ tài liệu ĐHCĐ công khai, lưu trong kho cá nhân. Doanh thu so với doanh thu thuần; lợi nhuận so với dòng bạn
          chọn. Lũy kế = cộng các quý VNDirect từ quý 1 của năm; thiếu một quý thì dừng và ghi rõ, không ước lượng phần còn lại của năm.</p>
      </details>
    </div>
  );
}
