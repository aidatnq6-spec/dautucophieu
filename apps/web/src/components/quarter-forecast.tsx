"use client";
import { type FormEvent, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";

export type Forecast = { symbol: string; version: number; quarter: string | null; base?: string | null; assumptions: Record<string, string> | null;
  values: Record<string, string | null>; labels: Record<string, string>; reason: string | null;
  earlier: { quarter: string; revenue: { forecast: string | null; actual: string | null }; npat_parent: { forecast: string | null; actual: string | null } }[] };

const PERCENT = new Set(["revenue_yoy", "gross_margin", "selling_pct", "admin_pct", "tax_rate", "minority_pct"]);
const ORDER = ["revenue_yoy", "gross_margin", "selling_pct", "admin_pct", "fin_income", "fin_expense", "interest", "associates", "other_profit",
  "tax_rate", "minority_pct", "depreciation"];

/** What the owner typed (percent for rates, tỷ đồng for amounts) as the decimals the server keeps; blanks left out. */
export function fromForm(form: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, raw] of Object.entries(form)) {
    const v = raw.trim().replace(",", ".");
    if (!v) continue;
    out[k] = PERCENT.has(k) ? String(Number((Number(v) / 100).toPrecision(12))) : v;
  }
  return out;
}

export function toForm(saved: Record<string, string> | null): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(saved ?? {})) out[k] = PERCENT.has(k) ? String(Number((Number(v) * 100).toPrecision(12))).replace(".", ",") : v;
  return out;
}

const ty = (v: string | null) => (v === null ? "—" : `${(Math.round(Number(v) / 1e9) || 0).toLocaleString("vi-VN")} tỷ`);
const qLabel = (q: string) => `Q${q.slice(-1)}/${q.slice(0, 4)}`;

export function ForecastForm({ symbol, data, onSaved }: { symbol: string; data: Forecast; onSaved: (f: Forecast) => void }) {
  const [form, setForm] = useState<Record<string, string>>(toForm(data.assumptions));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (!data.quarter) return <p className="muted">Dự phóng quý tới: {data.reason}.</p>;
  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      onSaved(await api<Forecast>(`quarter-forecast/${encodeURIComponent(symbol)}/${data.quarter}`, { method: "PUT",
        body: { assumptions: fromForm(form), expected_version: data.version, request_id: requestId() } }));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.failure.message : "Không lưu được.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <details className="mc-table" open={!data.assumptions}>
      <summary>Dự phóng {qLabel(data.quarter)} (giả định của bạn){data.assumptions ? " · đã nhập" : " · chưa nhập"}</summary>
      <form className="ap-form" onSubmit={save} aria-label="Giả định dự phóng quý tới">
        {ORDER.map((k) => <label key={k} className="field"><span>{data.labels[k]} ({PERCENT.has(k) ? "%" : "tỷ đồng"})</span>
          <input value={form[k] ?? ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} inputMode="decimal" /></label>)}
        <button type="submit" className="btn primary" disabled={busy}>Lưu giả định</button>
      </form>
      {error && <p className="errors" role="alert">{error}</p>}
      {data.reason && <p className="muted">{data.reason}.</p>}
      {data.earlier.length > 0 && <ul className="ft-checks">{data.earlier.map((e) => <li key={e.quarter}>{qLabel(e.quarter)}: dự phóng của bạn doanh thu {ty(e.revenue.forecast)},
        LNST công ty mẹ {ty(e.npat_parent.forecast)} · thực tế {ty(e.revenue.actual)}, {ty(e.npat_parent.actual)}</li>)}</ul>}
      <p className="caption wrap">Kịch bản của bạn, không phải dự báo của ứng dụng: ứng dụng không tự điền giả định; ô để trống thì các dòng dựa vào nó để trống.
        Doanh thu = cùng quý năm trước × (1 + tăng trưởng); giá vốn theo biên gộp; chi phí bán hàng, quản lý theo % doanh thu; LNTT = LN HĐKD lõi + doanh thu
        tài chính − chi phí tài chính + liên doanh liên kết + LN khác; LNST công ty mẹ = LNTT × (1 − thuế suất) × (1 − phần cổ đông không kiểm soát);
        EBIT = LNTT + lãi vay; EBITDA = EBIT + khấu hao. Khi quý có số thật, dự phóng của bạn hiện bên cạnh để so.</p>
    </details>
  );
}
