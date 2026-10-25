"use client";
import { useState } from "react";
import { Calculator, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { ApiError, api, requestId, type ApiFailure } from "../lib/api";
import { formatVnd, parseMoneyInput } from "../lib/format";
import { FormErrors } from "./form-errors";

type AssetRow = { asset_id: string; kind: string; amount: string; liquidity: string; inLedger: boolean; emergency: string };
type GoalRow = { goal_id: string; due_date: string; amount: string; funded: string; preserve_capital: boolean; deferrable: boolean; confirmed: boolean };
type Line = { kind: string; ref: string; amount: string; reason: string };
export type Assessment = { status: string; investable_capital: string | null; shortfall: string | null; gross_included: string;
  deductions_total: string; net: string; lines: Line[]; warnings: { code: string; amount: string }[] };

const KINDS = [["deposit", "Tiền gửi"], ["cash", "Tiền mặt"], ["bond", "Trái phiếu"], ["fund", "Chứng chỉ quỹ"], ["equity", "Cổ phiếu"],
  ["real_estate", "Bất động sản"], ["other", "Khác"]];
const LIQUIDITY = [["liquid", "Thanh khoản cao"], ["illiquid", "Khó bán nhanh"], ["consumption", "Tài sản tiêu dùng/nhà ở"]];
export const STATUS_LABEL: Record<string, string> = { ready: "Có vốn phù hợp để đầu tư", not_suitable: "Chưa có vốn phù hợp để bổ sung cổ phiếu",
  needs_confirmation: "Cần xác nhận mục tiêu", incomplete: "Thiếu giá trị sổ danh mục" };
export const REASON_LABEL: Record<string, string> = { liquid_asset: "Tài sản thanh khoản", counted_in_ledger: "Đã tính qua sổ danh mục",
  illiquid_asset: "Khó thanh khoản — không thuộc mẫu số", consumption_asset: "Tài sản tiêu dùng — không thuộc mẫu số",
  ledger_market_value: "Giá trị sổ danh mục", emergency_reserve: "Quỹ dự phòng", due_within_12_months: "Cần trong 12 tháng",
  capital_preservation: "Cần bảo toàn vốn", not_deferrable: "Không thể trì hoãn", flexible_beyond_12_months: "Sau 12 tháng, linh hoạt — không trừ" };
export const WARNING_LABEL: Record<string, string> = { emergency_reserve_not_liquid: "Một phần quỹ dự phòng nằm trong cổ phiếu/tài sản khó bán",
  emergency_reserve_shortfall: "Quỹ dự phòng dành riêng chưa đủ" };

let counter = 0;
const nextId = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${counter++}`;
const blankAsset = (): AssetRow => ({ asset_id: nextId("asset"), kind: "deposit", amount: "", liquidity: "liquid", inLedger: false, emergency: "" });
const blankGoal = (): GoalRow => ({ goal_id: nextId("goal"), due_date: "", amount: "", funded: "", preserve_capital: false, deferrable: false, confirmed: false });

export function BreakdownTable({ assessment }: { assessment: Assessment }) {
  return (
    <div className="tablewrap">
      <table aria-label="Bảng tính vốn có thể đầu tư">
        <thead><tr><th>Khoản</th><th>Loại</th><th>Lý do</th><th className="num">Số tiền</th></tr></thead>
        <tbody>
          {assessment.lines.map((l, i) => (
            <tr key={`${l.ref}-${i}`}>
              <td className="wrap">{l.ref}</td>
              <td>{{ included: "Tính vào", excluded: "Không tính", deduction: "Trừ ra", not_deducted: "Không trừ" }[l.kind] ?? l.kind}</td>
              <td className="wrap">{REASON_LABEL[l.reason] ?? l.reason}</td>
              <td className="num">{l.kind === "deduction" ? "−" : ""}{formatVnd(l.amount)}</td>
            </tr>
          ))}
          <tr><td colSpan={3}><strong>Vốn có thể đầu tư</strong> (tổng tính vào − tổng trừ ra)</td>
            <td className="num"><strong>{formatVnd(assessment.net)}</strong></td></tr>
        </tbody>
      </table>
    </div>
  );
}

export function ProfileForm({ version, onSaved }: { version: number; onSaved: () => void }) {
  const [asOf, setAsOf] = useState(() => new Date().toISOString().slice(0, 10));
  const [reserve, setReserve] = useState("");
  const [ledgerValue, setLedgerValue] = useState("");
  const [assets, setAssets] = useState<AssetRow[]>([blankAsset()]);
  const [goals, setGoals] = useState<GoalRow[]>([]);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [failure, setFailure] = useState<ApiFailure | null>(null);
  const [local, setLocal] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  function build() {
    const problems: string[] = [];
    const money = (label: string, raw: string, required = true) => {
      if (!raw.trim()) { if (required) problems.push(`${label}: chưa nhập`); return "0"; }
      const v = parseMoneyInput(raw);
      if (v === null) problems.push(`${label}: số tiền không hợp lệ`);
      return v ?? "0";
    };
    const emergency = money("Quỹ dự phòng", reserve);
    const funding: { source_id: string; amount: string }[] = [];
    const payloadGoals = goals.map((g, i) => {
      const funded = money(`Mục tiêu ${i + 1} — nguồn bù`, g.funded, false);
      if (!g.due_date) problems.push(`Mục tiêu ${i + 1}: chưa có ngày`);
      if (funded !== "0") funding.push({ source_id: `src-${g.goal_id}`, amount: funded });
      return { goal_id: g.goal_id, due_date: g.due_date, amount: money(`Mục tiêu ${i + 1} — số tiền`, g.amount), preserve_capital: g.preserve_capital,
        deferrable: g.deferrable, confirmed: g.confirmed, funding: funded !== "0" ? [{ source_id: `src-${g.goal_id}`, amount: funded }] : [] };
    });
    const payloadAssets = assets.map((a, i) => {
      const e = money(`Tài sản ${i + 1} — phần dự phòng`, a.emergency, false);
      return { asset_id: a.asset_id, kind: a.kind, amount: money(`Tài sản ${i + 1} — số tiền`, a.amount), liquidity: a.liquidity,
        ledger_link: a.inLedger ? "ledger-main" : null, earmarks: e !== "0" ? [{ purpose: "emergency", amount: e }] : [] };
    });
    const ledger = ledgerValue.trim() ? parseMoneyInput(ledgerValue) : null;
    if (ledgerValue.trim() && ledger === null) problems.push("Giá trị sổ danh mục: số tiền không hợp lệ");
    setLocal(problems);
    if (problems.length) return null;
    return { profile: { as_of: asOf, emergency_reserve: emergency, assets: payloadAssets, goals: payloadGoals, funding_sources: funding }, ledger_value: ledger };
  }

  async function preview() {
    const body = build();
    setFailure(null);
    if (!body) return;
    setBusy(true);
    try { setAssessment(await api<Assessment>("profile/assessment", { method: "POST", body })); }
    catch (e) { setAssessment(null); if (e instanceof ApiError) setFailure(e.failure); }
    finally { setBusy(false); }
  }

  async function confirm() {
    const body = build();
    if (!body || !assessment) return;
    setBusy(true);
    try {
      await api("profile", { method: "PUT", body: { ...body, reviewed_net: assessment.net, expected_version: version, request_id: requestId() } });
      onSaved();
    } catch (e) { if (e instanceof ApiError) setFailure(e.failure); }
    finally { setBusy(false); }
  }

  const changed = () => setAssessment(null); // any edit invalidates the reviewed breakdown
  const updateAsset = (i: number, patch: Partial<AssetRow>) => { setAssets((rows) => rows.map((r, j) => (j === i ? { ...r, ...patch } : r))); changed(); };
  const updateGoal = (i: number, patch: Partial<GoalRow>) => { setGoals((rows) => rows.map((r, j) => (j === i ? { ...r, ...patch } : r))); changed(); };

  return (
    <form onSubmit={(e) => { e.preventDefault(); void preview(); }} aria-label="Hồ sơ tài chính">
      <FormErrors failure={failure} local={local} />
      <div className="formgrid">
        <label className="field">Ngày hiệu lực<input type="date" value={asOf} onChange={(e) => { setAsOf(e.target.value); changed(); }} required /></label>
        <label className="field">Quỹ dự phòng cần giữ (đ)<input name="emergency_reserve" inputMode="numeric" value={reserve}
          onChange={(e) => { setReserve(e.target.value); changed(); }} placeholder="200.000.000" /></label>
        <label className="field">Giá trị sổ danh mục theo giá thị trường (đ)<input inputMode="numeric" value={ledgerValue}
          onChange={(e) => { setLedgerValue(e.target.value); changed(); }} placeholder="Để trống nếu chưa có" /></label>
      </div>

      <h3>Tài sản</h3>
      {assets.map((a, i) => (
        <fieldset key={a.asset_id}>
          <legend>Tài sản {i + 1}</legend>
          <div className="formgrid">
            <label className="field">Loại<select value={a.kind} onChange={(e) => updateAsset(i, { kind: e.target.value })}>
              {KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="field">Số tiền (đ)<input inputMode="numeric" value={a.amount} onChange={(e) => updateAsset(i, { amount: e.target.value })} /></label>
            <label className="field">Thanh khoản<select value={a.liquidity} onChange={(e) => updateAsset(i, { liquidity: e.target.value })}>
              {LIQUIDITY.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="field">Phần dành cho quỹ dự phòng (đ)<input inputMode="numeric" value={a.emergency}
              onChange={(e) => updateAsset(i, { emergency: e.target.value })} /></label>
          </div>
          <label className="choice"><input type="checkbox" checked={a.inLedger} onChange={(e) => updateAsset(i, { inLedger: e.target.checked })} />
            Tài khoản chứng khoán đã theo dõi trong sổ (không cộng lần hai)</label>
          {assets.length > 1 && <button type="button" className="btn text" onClick={() => { setAssets((r) => r.filter((_, j) => j !== i)); changed(); }}>
            <Trash2 size={16} aria-hidden="true" />Bỏ tài sản này</button>}
        </fieldset>
      ))}
      <button type="button" className="btn" onClick={() => { setAssets((r) => [...r, blankAsset()]); changed(); }}><Plus size={16} aria-hidden="true" />Thêm tài sản</button>

      <h3>Mục tiêu và khoản chi lớn</h3>
      <p className="caption">Nhập số tiền còn thiếu sau nguồn thu chắc chắn đã dành; chi thường xuyên đã được thu nhập đáp ứng thì không cần nhập.</p>
      {goals.map((g, i) => (
        <fieldset key={g.goal_id}>
          <legend>Mục tiêu {i + 1}</legend>
          <div className="formgrid">
            <label className="field">Ngày cần tiền<input type="date" value={g.due_date} onChange={(e) => updateGoal(i, { due_date: e.target.value })} /></label>
            <label className="field">Số tiền cần (đ)<input inputMode="numeric" value={g.amount} onChange={(e) => updateGoal(i, { amount: e.target.value })} /></label>
            <label className="field">Nguồn bù đã dành (đ)<input inputMode="numeric" value={g.funded} onChange={(e) => updateGoal(i, { funded: e.target.value })} /></label>
          </div>
          <label className="choice"><input type="checkbox" checked={g.preserve_capital} onChange={(e) => updateGoal(i, { preserve_capital: e.target.checked })} />Cần bảo toàn vốn</label>
          <label className="choice"><input type="checkbox" checked={g.deferrable} onChange={(e) => updateGoal(i, { deferrable: e.target.checked })} />Có thể trì hoãn</label>
          <label className="choice"><input type="checkbox" checked={g.confirmed} onChange={(e) => updateGoal(i, { confirmed: e.target.checked })} />Tôi xác nhận ngày và số tiền</label>
          <button type="button" className="btn text" onClick={() => { setGoals((r) => r.filter((_, j) => j !== i)); changed(); }}><Trash2 size={16} aria-hidden="true" />Bỏ mục tiêu</button>
        </fieldset>
      ))}
      <button type="button" className="btn" onClick={() => { setGoals((r) => [...r, blankGoal()]); changed(); }}><Plus size={16} aria-hidden="true" />Thêm mục tiêu</button>

      <div className="actions"><button type="submit" className="btn" disabled={busy}><Calculator size={16} aria-hidden="true" />Xem bảng tính vốn</button></div>

      {assessment && (
        <section className="surface" aria-live="polite" style={{ marginTop: 18 }}>
          <div className="row"><h2>Bảng tính để bạn duyệt</h2>
            <span className={`pill ${assessment.status === "ready" ? "good" : "warn"}`}>{STATUS_LABEL[assessment.status] ?? assessment.status}</span></div>
          <BreakdownTable assessment={assessment} />
          {assessment.warnings.map((w) => <p key={w.code} className="notice">{WARNING_LABEL[w.code] ?? w.code}: {formatVnd(w.amount)}</p>)}
          <div className="actions">
            <button type="button" className="btn primary" disabled={busy || !["ready", "not_suitable"].includes(assessment.status)} onClick={() => void confirm()}>
              <ShieldCheck size={16} aria-hidden="true" />Xác nhận bảng tính này</button>
          </div>
        </section>
      )}
    </form>
  );
}
