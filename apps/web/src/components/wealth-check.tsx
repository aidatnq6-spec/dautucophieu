"use client";
import { useEffect, useRef, useState } from "react";
import { HeartPulse } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";

type Check = { age: number; savings: string; rate: string; target: string; status: "ok" | "short" | "none"; gap: string | null; surplus: string | null };
type View = { version: number; inputs: { income: string; expenses: string; birth_year: number } | null; check: Check | null };

const pct = (r: string) => formatRatio(r, 1).replace(",0%", "%");

/** Savings rate against VWA's rule of thumb (at least one's age in percent). The owner's own figures; it reports, never advises. */
export function WealthCheck({ onSaved }: { onSaved?: () => void } = {}) {
  const [view, setView] = useState<View | null>(null);
  const [income, setIncome] = useState("");
  const [expenses, setExpenses] = useState("");
  const [year, setYear] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const filled = useRef(false);  // saved figures fill the inputs once; a later load must not overwrite what is being typed
  useEffect(() => {
    api<View>("wealth-check").then((v) => {
      setView((current) => current ?? v);
      if (v.inputs && !filled.current) { filled.current = true; setIncome(formatVnd(v.inputs.income, { unit: false })); setExpenses(formatVnd(v.inputs.expenses, { unit: false })); setYear(String(v.inputs.birth_year)); }
    }, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  async function save() {
    if (!view) return;
    const i = parseMoneyInput(income), e = parseMoneyInput(expenses), y = Number(year);
    if (i === null || e === null || i.includes(".") || e.includes(".") || !/^\d{4}$/.test(year)) {
      setMessage("Nhập thu nhập và chi tiêu bằng số đồng, năm sinh 4 chữ số."); return;
    }
    try {
      setView(await api<View>("wealth-check", { method: "PUT", body: { income: i, expenses: e, birth_year: y, expected_version: view.version, request_id: requestId() } }));
      setMessage(null); onSaved?.();
    } catch (err) { setMessage(err instanceof ApiError ? err.failure.message : "Lỗi lưu."); }
  }
  const c = view?.check;
  return (
    <section className="surface" aria-label="Sức khỏe tài chính">
      <h2>Sức khỏe tài chính</h2>
      <p className="caption">Tỷ lệ tích lũy hằng tháng so với quy tắc kinh nghiệm của VWA: tỷ lệ tích lũy nên ít nhất bằng số tuổi (37 tuổi → từ 37% thu nhập).
        Đây là quy tắc kinh nghiệm, không phải chuẩn bắt buộc hay khuyến nghị.</p>
      <form className="eb-form" onSubmit={(ev) => { ev.preventDefault(); void save(); }}>
        <label className="field">Thu nhập hằng tháng (đ)<input inputMode="numeric" value={income} disabled={!view} onChange={(ev) => setIncome(groupDigitsInput(ev.target.value))} /></label>
        <label className="field">Chi tiêu hằng tháng (đ)<input inputMode="numeric" value={expenses} disabled={!view} onChange={(ev) => setExpenses(groupDigitsInput(ev.target.value))} /></label>
        <label className="field">Năm sinh<input inputMode="numeric" maxLength={4} value={year} disabled={!view} onChange={(ev) => setYear(ev.target.value.replace(/\D/g, ""))} /></label>
        <button type="submit" className="btn primary" disabled={!view}><HeartPulse size={16} aria-hidden="true" />Kiểm tra</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {c && <dl className="eb-result">
        <div><dt>Tích lũy mỗi tháng</dt><dd data-testid="wc-savings">{c.savings.startsWith("-") ? `−${formatVnd(c.savings.slice(1))}` : formatVnd(c.savings)}</dd></div>
        <div><dt>Tỷ lệ tích lũy</dt><dd data-testid="wc-rate">{pct(c.rate)}</dd></div>
        <div><dt>Mục tiêu theo tuổi ({c.age})</dt><dd data-testid="wc-target">≥ {pct(c.target)}</dd></div>
        <div className="eb-main"><dt>Kết quả</dt><dd data-testid="wc-result" className={c.status === "ok" ? "positive" : "negative"}>
          {c.status === "ok" ? `Đạt: vượt mục tiêu ${formatVnd(c.surplus)}/tháng`
            : c.status === "short" ? `Chưa đạt: cần tích lũy thêm ${formatVnd(c.gap)}/tháng`
            : `Chưa có tích lũy: cần thêm ${formatVnd(c.gap)}/tháng để đạt mục tiêu`}</dd></div>
      </dl>}
    </section>
  );
}
