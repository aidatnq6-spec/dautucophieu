"use client";
import { useEffect, useState } from "react";
import { Calculator } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";
import { GROUP_LABEL } from "./risk-survey";

type Budget = { status: "no_total" | "no_risk" | "ok"; total?: string; deductions?: string; base?: string; group?: string; ratio?: string;
  budget?: string; held_cost?: string; held_weight?: string | null; room?: string | null; over?: string | null;
  deductions_source?: "manual" | "profile"; profile_deductions?: string; reserve?: string | null };
type View = { version: number; budget: Budget };

const pct = (r: string) => formatRatio(r, 1).replace(",0%", "%");

/** Total financial assets → money for stocks by risk group. Holdings at cost; an excess is shown, never a sell. */
export function EquityBudget() {
  const [view, setView] = useState<View | null>(null);
  const [value, setValue] = useState("");
  const [reserve, setReserve] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>("equity-budget").then((v) => { setView(v); if (v.budget.total) setValue(formatVnd(v.budget.total, { unit: false }));
      if (v.budget.reserve) setReserve(formatVnd(v.budget.reserve, { unit: false })); },
      (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  async function save() {
    if (!view) return;
    const total = parseMoneyInput(value);
    if (total === null || total.startsWith("-") || total.includes(".")) { setMessage("Nhập số đồng, ví dụ 2.000.000.000."); return; }
    const manual = reserve.trim() ? parseMoneyInput(reserve) : null;  // empty = use the profile's figure
    if (reserve.trim() && (manual === null || manual.includes("."))) { setMessage("Quỹ dự phòng: nhập số đồng, hoặc để trống."); return; }
    try {
      setView(await api<View>("equity-budget", { method: "PUT", body: { total, reserve: manual, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const b = view?.budget;
  return (
    <section className="surface" aria-label="Vốn dành cho cổ phiếu">
      <h2>Vốn dành cho cổ phiếu</h2>
      <p className="caption">Tổng tài sản tài chính gồm tiền gửi, trái phiếu, cổ phiếu, vàng, tiền số. Trừ quỹ dự phòng và các khoản phải chi trong 12 tháng
        (theo hồ sơ tài chính, hoặc số bạn nhập tay bên dưới), rồi nhân tỷ trọng cổ phiếu của nhóm khẩu vị. Trang Danh mục tính tỷ trọng từng mã trên con số này.</p>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <label className="field">Tổng tài sản tài chính (đ)<input inputMode="numeric" value={value} onChange={(e) => setValue(groupDigitsInput(e.target.value))} disabled={!view} /></label>
        <label className="field">Quỹ dự phòng và khoản chi 12 tháng (đ)<input inputMode="numeric" value={reserve} disabled={!view}
          onChange={(e) => setReserve(groupDigitsInput(e.target.value))}
          placeholder={b?.profile_deductions ? `để trống = theo hồ sơ (${formatVnd(b.profile_deductions)})` : "để trống = theo hồ sơ"} /></label>
        <button type="submit" className="btn primary" disabled={!view}><Calculator size={16} aria-hidden="true" />Tính vốn cho cổ phiếu</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {b?.status === "no_risk" && <p className="notice">Chưa có kết quả khảo sát rủi ro nên chưa biết tỷ trọng cổ phiếu.</p>}
      {b?.status === "ok" && <dl className="eb-result">
        <div><dt>Tổng tài sản tài chính</dt><dd>{formatVnd(b.total)}</dd></div>
        <div><dt>Trừ quỹ dự phòng và khoản chi 12 tháng <span className="caption">({b.deductions_source === "manual" ? "nhập tay" : "theo hồ sơ"})</span></dt>
          <dd data-testid="equity-deductions">{b.deductions === "0" ? "0 đ" : `−${formatVnd(b.deductions)}`}</dd></div>
        <div><dt>Nhóm khẩu vị</dt><dd>{GROUP_LABEL[b.group!] ?? b.group} → tỷ trọng cổ phiếu {pct(b.ratio!)}</dd></div>
        <div className="eb-main"><dt>Vốn dành cho cổ phiếu</dt><dd data-testid="equity-budget">{formatVnd(b.budget)}</dd></div>
        <div><dt>Đang nắm (theo giá mua): {formatVnd(b.held_cost)}{b.held_weight ? ` (${pct(b.held_weight)})` : ""}</dt>
          <dd>{b.over ? <span className="negative">Đã vượt {formatVnd(b.over)}</span> : <>còn có thể mua thêm {formatVnd(b.room)}</>}</dd></div>
      </dl>}
    </section>
  );
}
