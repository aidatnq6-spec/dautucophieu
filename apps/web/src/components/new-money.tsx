"use client";
import { useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";

type Step = { id: string; amount: string; why: "reserve" | "short" | "room" | "rest" };
type After = { id: string; status: string; gap: string | null };
type Result = { status: "ok" | "no_total" | "no_risk" | "no_layers"; steps?: Step[]; allocated?: string; after?: After[]; reserve_checked?: boolean };

const NAME: Record<string, string> = { reserve: "Quỹ dự phòng", deposit: "Tiền gửi", bond: "Trái phiếu", gold: "Vàng", stocks: "Cổ phiếu", crypto: "Tiền số" };
const WHY: Record<Step["why"], string> = { reserve: "tiền rút được ngay còn thiếu so với quỹ dự phòng", short: "bù lên mức tối thiểu của lớp", room: "các lớp đã đủ mức tối thiểu, thêm tới mức trần của cổ phiếu", rest: "phần còn lại vào tiền gửi" };
const MISSING: Record<string, string> = { no_total: "Chưa có Tháp tài sản: nhập Sổ tài sản hoặc các lớp bên trên.", no_risk: "Tháp tài sản chưa tính được vì chưa có nhóm rủi ro.", no_layers: "Tháp tài sản đang dùng một con số tổng, chưa có từng lớp để chia." };
const STATE: Record<string, string> = { short: "vẫn thiếu", ok: "đủ", over: "vượt" };

/** Tiền mới tháng này đi đâu: new money from the bottom of Tháp tài sản up. A calculation on the owner's figures: nothing is saved and no ticker is named. */
export function NewMoney() {
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function run() {
    const amount = parseMoneyInput(raw);
    if (amount === null || amount.includes(".") || Number(amount) <= 0) { setResult(null); setMessage("Nhập số đồng lớn hơn 0."); return; }
    setBusy(true); setMessage(null);
    try { setResult(await api<Result>("equity-budget/new-money", { method: "POST", body: { amount } })); }
    catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tính."); } finally { setBusy(false); }
  }
  const left = result?.after?.filter((l) => l.status === "short") ?? [];
  return (
    <section className="surface" aria-label="Tiền mới tháng này đi đâu">
      <h2>Tiền mới tháng này đi đâu</h2>
      <p className="caption">Chia từ dưới lên theo Tháp tài sản: quỹ dự phòng, rồi các lớp đang dưới mức tối thiểu; khi đã đủ thì thêm cổ phiếu tới mức trần, phần còn lại vào tiền gửi. Phép tính trên số bạn đã nhập, không lưu và không phải khuyến nghị.</p>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void run(); }}>
        <label className="field">Số tiền mới (đ)<input inputMode="numeric" value={raw} onChange={(e) => setRaw(groupDigitsInput(e.target.value))} /></label>
        <button type="submit" className="btn primary" disabled={busy}>Chia theo Tháp tài sản</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {result && result.status !== "ok" && <p className="notice pv-note">{MISSING[result.status]}</p>}
      {result?.status === "ok" && <>
        <dl className="eb-result">
          {result.steps!.map((s, i) => <div key={`${s.id}-${i}`}><dt>{NAME[s.id]} <span className="caption">({WHY[s.why]})</span></dt><dd>{formatVnd(s.amount)}</dd></div>)}
          <div className="eb-main"><dt>Tổng đã chia</dt><dd data-testid="nm-total">{formatVnd(result.allocated!)}</dd></div>
        </dl>
        {left.length > 0 && <p className="caption">Sau khi chia vẫn còn thiếu: {left.map((l) => `${NAME[l.id] ?? l.id} ${formatVnd(l.gap)}`).join(", ")}.</p>}
        {left.length === 0 && <p className="caption">Sau khi chia, các lớp đều {result.after!.some((l) => l.status === "over") ? `đạt mức tối thiểu; còn vượt mục tiêu: ${result.after!.filter((l) => l.status === "over").map((l) => NAME[l.id] ?? l.id).join(", ")}` : STATE.ok}.</p>}
        {!result.reserve_checked && <p className="caption">Chưa có Sổ tài sản nên chưa so được tiền rút ngay với quỹ dự phòng.</p>}
      </>}
    </section>
  );
}
