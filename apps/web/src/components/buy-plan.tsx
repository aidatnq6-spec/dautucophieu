"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";

type Kind = "price_le" | "report" | "date";
export type Tranche = { id: string; symbol: string; amount: string; kind: Kind; value: string; note: string; status: "waiting" | "met" | "done" | "dropped";
  met_on: string | null; met_value: string | null; close: string | null; close_date: string | null; distance: string | null; days_left: number | null };
type Plan = { version: number; tranches: Tranche[] };

const KIND: Record<Kind, string> = { price_le: "Giá đóng cửa ≤", report: "Có báo cáo quý", date: "Từ ngày" };
const STATUS: Record<Tranche["status"], [string, string]> = { waiting: ["Chờ", ""], met: ["Đã đến điều kiện", "good"], done: ["Đã mua", "good"], dropped: ["Bỏ", "bad"] };
const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** The condition as typed into a stored value: a price with a decimal comma becomes "90.5"; a quarter "Q4/2026" becomes "2026-Q4". */
export function conditionValue(kind: Kind, raw: string): string {
  const v = raw.trim();
  if (kind === "price_le") return v.replace(/\./g, "").replace(",", ".");
  if (kind === "report") { const m = v.match(/^Q?([1-4])\s*\/\s*(\d{4})$/i); return m ? `${m[2]}-Q${m[1]}` : v.toUpperCase(); }
  return v;
}

/** Where a waiting tranche stands: how far the close is above the level, or the days left. */
export function standing(t: Tranche): string {
  if (t.status === "met") return `Đạt ngày ${dmy(t.met_on!)}${t.kind === "price_le" ? ` (đóng cửa ${formatDecimal(t.met_value!, 2)})` : ""}`;
  if (t.kind === "price_le") return t.close === null ? "chưa có giá đóng cửa" : `đóng cửa ${formatDecimal(t.close, 2)} ngày ${dmy(t.close_date!)}`
    + (t.distance !== null && Number(t.distance) < 0 ? `, cần giảm thêm ${formatRatio(t.distance.replace("-", ""), 1)}` : "");
  if (t.kind === "date") return `còn ${t.days_left} ngày`;
  return "chờ báo cáo";
}

const asSent = (t: Tranche, status?: Tranche["status"]) => ({ id: t.id, symbol: t.symbol, amount: t.amount, kind: t.kind, value: t.value, note: t.note,
  ...(status ? { status } : {}) });

export function BuyPlan() {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ symbol: "", amount: "", kind: "price_le" as Kind, value: "", note: "" });
  const [busy, setBusy] = useState(false);
  useEffect(() => { api<Plan>("buy-plan").then(setPlan, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const save = async (tranches: object[]) => {
    if (!plan) return false;
    setBusy(true); setError(null);
    try {
      setPlan(await api<Plan>("buy-plan", { method: "PUT", body: { tranches, expected_version: plan.version, request_id: requestId() } }));
      return true;
    } catch (e) { setError(e instanceof ApiError ? e.failure.message : "Không lưu được."); return false; } finally { setBusy(false); }
  };
  const add = async () => {
    const amount = parseMoneyInput(form.amount);
    if (!amount) { setError("Nhập số tiền định mua."); return; }
    const ok = await save([...(plan?.tranches ?? []).map((t) => asSent(t)), { id: requestId().slice(0, 32), symbol: form.symbol, amount, kind: form.kind,
      value: conditionValue(form.kind, form.value), note: form.note }]);
    if (ok) setForm({ ...form, symbol: "", amount: "", value: "", note: "" });
  };
  const set = (id: string, status?: Tranche["status"]) => void save(plan!.tranches.map((t) => asSent(t, t.id === id ? status : undefined)));
  return (
    <section className="surface" aria-label="Kế hoạch giải ngân">
      <h2>Kế hoạch giải ngân theo điều kiện</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!plan && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {plan && <>
        <form className="formgrid" aria-label="Thêm đợt mua" onSubmit={(e) => { e.preventDefault(); void add(); }}>
          <label className="field">Mã<input aria-label="Mã" value={form.symbol} maxLength={10} onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })} /></label>
          <label className="field">Số tiền (đ)<input aria-label="Số tiền" inputMode="numeric" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: groupDigitsInput(e.target.value) })} /></label>
          <label className="field">Điều kiện<select aria-label="Điều kiện" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as Kind, value: "" })}>
            {(Object.keys(KIND) as Kind[]).map((k) => <option key={k} value={k}>{KIND[k]}</option>)}</select></label>
          <label className="field">{form.kind === "price_le" ? "Giá (nghìn đồng)" : form.kind === "report" ? "Quý (Q4/2026)" : "Ngày"}
            <input aria-label="Giá trị điều kiện" type={form.kind === "date" ? "date" : "text"} value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} /></label>
          <label className="field">Ghi chú<input aria-label="Ghi chú đợt" maxLength={200} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
          <button type="submit" className="btn" disabled={busy}>Thêm đợt</button>
        </form>
        {plan.tranches.length === 0 ? <p className="muted">Chưa có đợt mua nào.</p> : <table className="fv-table" aria-label="Các đợt mua dự kiến">
          <thead><tr><th>Mã</th><th className="num">Số tiền</th><th>Điều kiện</th><th>Hiện trạng</th><th>Trạng thái</th><th /></tr></thead>
          <tbody>{plan.tranches.map((t) => <tr key={t.id}>
            <td data-label="Mã"><Link href={`/research/${t.symbol}`}>{t.symbol}</Link>{t.note && <div className="caption">{t.note}</div>}</td>
            <td className="num" data-label="Số tiền">{formatVnd(t.amount)}</td>
            <td data-label="Điều kiện">{KIND[t.kind]} {t.kind === "price_le" ? formatDecimal(t.value, 2) : t.kind === "date" ? dmy(t.value) : `Q${t.value.slice(-1)}/${t.value.slice(0, 4)}`}</td>
            <td data-label="Hiện trạng">{t.status === "waiting" || t.status === "met" ? standing(t) : "—"}</td>
            <td data-label="Trạng thái">{STATUS[t.status][1] ? <span className={`pill ${STATUS[t.status][1]}`}>{STATUS[t.status][0]}</span> : STATUS[t.status][0]}</td>
            <td data-label="Thao tác"><div className="ib-actions">
              {t.status !== "done" && <button type="button" className="btn" disabled={busy} onClick={() => set(t.id, "done")}>Đã mua</button>}
              {t.status !== "dropped" && t.status !== "done" && <button type="button" className="btn" disabled={busy} onClick={() => set(t.id, "dropped")}>Bỏ</button>}
              {(t.status === "done" || t.status === "dropped" || t.status === "met") && <button type="button" className="btn" disabled={busy} onClick={() => set(t.id, "waiting")}>Chờ lại</button>}
              <button type="button" className="btn" aria-label={`Xóa đợt ${t.symbol}`} disabled={busy}
                onClick={() => { if (window.confirm(`Xóa đợt mua ${t.symbol}?`)) void save(plan.tranches.filter((x) => x.id !== t.id).map((x) => asSent(x))); }}>Xóa</button>
            </div></td></tr>)}</tbody>
        </table>}
        <p className="caption">Sau mỗi phiên (15:30 và 20:00) phần mềm kiểm điều kiện bằng giá đóng cửa và báo cáo đã lưu; đợt nào vừa đạt được báo một lần qua Telegram.
          Phần mềm không đặt lệnh: bạn tự quyết, rồi đánh dấu Đã mua hoặc Bỏ. Không phải khuyến nghị.</p>
      </>}
    </section>
  );
}
