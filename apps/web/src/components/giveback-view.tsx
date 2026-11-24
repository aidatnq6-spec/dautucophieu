"use client";
import { useEffect, useState } from "react";
import { Check, Plus, X } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, hanoiDate, parseMoneyInput } from "../lib/format";
import { ruleLabel, type Rule } from "./basket-rules";

type Point = { gain: string; ratio: string | null; on: string };
export type Row = { symbol: string; since: string; reason: string | null; never_gained: boolean; sessions_since_peak: number | null;
  peak: Point | null; now: Point | null; given_back: string | null; share: string | null; days: { on: string; gain: string }[]; rule?: Rule };
type Portfolio = Omit<Row, "symbol" | "since" | "reason" | "days"> & { skipped: number; missing: string[]; days: { on: string; gain: string; value: string }[] };
export type GoalStatus = { enough: boolean | null; short: string | null; since: string | null; days: number | null; before_goal: boolean | null;
  last: { from: string; to: string; excess: string } | null; last_before_goal: boolean | null };
type Goal = { id: string; name: string; amount: string; basis: "value" | "gain"; created_on: string; closed: { kind: "done" | "dropped"; on: string } | null };
type Data = { rows: Row[]; portfolio: Portfolio; thresholds: { min_gain: string | null; share: string | null }; goals: (Goal & { status: GoalStatus })[];
  goals_version: number; as_of: string };

const BASIS = { value: "giá trị danh mục", gain: "lãi chưa chốt của danh mục" };
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const signed = (ratio: string) => `${ratio.startsWith("-") || !/[1-9]/.test(ratio) ? "" : "+"}${formatRatio(ratio, 1)}`;

export function peakLine(r: Pick<Row, "peak" | "never_gained" | "reason">): string {
  if (r.reason) return r.reason;
  if (r.never_gained) return "Chưa từng có lãi trong đợt nắm này";
  if (!r.peak) return "—";
  return `${formatVnd(r.peak.gain)}${r.peak.ratio ? ` (${signed(r.peak.ratio)})` : ""} ngày ${day(r.peak.on)}`;
}

export function backLine(r: Pick<Row, "given_back" | "share" | "sessions_since_peak">): string {
  if (r.given_back === null || r.share === null) return "—";
  if (!/[1-9]/.test(r.given_back)) return "Chưa trả lại: hôm nay là lãi cao nhất";
  return `${formatVnd(r.given_back)}, bằng ${formatRatio(r.share, 1)} lãi cao nhất · đỉnh lãi cách ${r.sessions_since_peak} phiên`;
}

export function byGivenBack(a: Pick<Row, "given_back">, b: Pick<Row, "given_back">): number {
  if (a.given_back === null || b.given_back === null) return a.given_back === null ? (b.given_back === null ? 0 : 1) : -1;
  return Number(b.given_back) - Number(a.given_back);
}

/** "150" → "1.5", "30,5" → "0.305": a percent with no upper bound, moved two places on the string. */
export function percentInput(raw: string): string | null {
  const v = parseMoneyInput(raw);
  if (v === null) return null;
  const [i, f = ""] = v.split(".");
  const digits = i.padStart(3, "0") + f;
  const whole = digits.slice(0, digits.length - f.length - 2).replace(/^0+(?=\d)/, "") || "0";
  const frac = digits.slice(digits.length - f.length - 2).replace(/0+$/, "");
  return frac ? `${whole}.${frac}` : whole;
}

export function goalLine(s: GoalStatus): string {
  if (s.enough === null) return "Chưa tính được: danh mục thiếu giá đã lưu";
  if (s.enough && s.since) return `Đã đủ từ ${day(s.since)}${s.before_goal ? ", trước khi bạn đặt mục tiêu" : s.days ? ` (${s.days} ngày)` : ""}`;
  const was = s.last ? ` · từng đủ từ ${day(s.last.from)} đến ${day(s.last.to)}, vượt tối đa ${formatVnd(s.last.excess)}${s.last_before_goal ? " (trước khi bạn đặt mục tiêu)" : ""}` : "";
  return `Còn thiếu ${formatVnd(s.short)}${was}`;
}

/** The gain day by day in the current holding period, with the zero line. */
function Spark({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const lo = Math.min(0, ...values), hi = Math.max(0, ...values), span = hi - lo || 1;
  const y = (v: number) => 28 - ((v - lo) / span) * 26;
  const line = values.map((v, i) => `${(i / (values.length - 1)) * 100},${y(v)}`).join(" ");
  return <svg className="ms-spark" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">
    <line x1="0" x2="100" y1={y(0)} y2={y(0)} className="ms-mark-yellow" /><polyline points={line} /></svg>;
}

function Goals({ d, onSaved }: { d: Data; onSaved: (d: Data) => void }) {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [basis, setBasis] = useState<"value" | "gain">("value");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const plain = (g: Goal): Goal => ({ id: g.id, name: g.name, amount: g.amount, basis: g.basis, created_on: g.created_on, closed: g.closed });
  async function save(goals: Goal[], done: string) {
    setBusy(true);
    try {
      onSaved(await api<Data>("spend-goals", { method: "PUT", body: { goals, expected_version: d.goals_version, request_id: requestId() } }));
      setMessage(done);
      return true;
    } catch (e) {
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu.");
      return false;
    } finally { setBusy(false); }
  }
  async function add() {
    const value = parseMoneyInput(amount);
    if (!name.trim() || value === null || !/[1-9]/.test(value)) { setMessage("Nhập tên và số tiền lớn hơn 0."); return; }
    const goal: Goal = { id: requestId(), name: name.trim(), amount: value, basis, created_on: hanoiDate(), closed: null };
    if (await save([...d.goals.map(plain), goal], "Đã thêm mục tiêu.")) { setName(""); setAmount(""); }
  }
  const close = (id: string, kind: "done" | "dropped") =>
    void save(d.goals.map((g) => g.id === id ? { ...plain(g), closed: { kind, on: hanoiDate() } } : plain(g)), kind === "done" ? "Đã ghi là đã thực hiện." : "Đã bỏ mục tiêu.");
  return (
    <div aria-label="Mục tiêu đã đủ tiền">
      <h3>Mục tiêu đã đủ tiền</h3>
      <p className="caption">Ghi một khoản bạn định chi (ví dụ mua nhà, mua xe). Ứng dụng cho biết danh mục đã đủ tiền cho khoản đó từ ngày nào, và nhắc
        qua Telegram một lần khi bắt đầu đủ, một lần khi đã đủ rồi lại thiếu. Không đụng Sổ tài sản hay Tháp tài sản.</p>
      {d.goals.length > 0 && <table className="fv-table cc-table" aria-label="Các mục tiêu">
        <thead><tr><th>Mục tiêu</th><th className="num">Số tiền</th><th>Tình trạng</th><th /></tr></thead>
        <tbody>{d.goals.map((g) => <tr key={g.id} className={g.status.enough && !g.closed ? "cc-over" : ""}>
          <td data-label="Mục tiêu"><strong>{g.name}</strong><div className="caption">theo {BASIS[g.basis]} · đặt ngày {day(g.created_on)}</div></td>
          <td data-label="Số tiền" className="num">{formatVnd(g.amount)}</td>
          <td data-label="Tình trạng">{g.closed ? <span className="muted">{g.closed.kind === "done" ? "Đã thực hiện" : "Đã bỏ"} ngày {day(g.closed.on)}</span>
            : goalLine(g.status)}</td>
          <td>{!g.closed && <div className="actions">
            <button className="btn" disabled={busy} onClick={() => close(g.id, "done")}><Check size={16} aria-hidden="true" />Đã thực hiện</button>
            <button className="btn" disabled={busy} onClick={() => close(g.id, "dropped")}><X size={16} aria-hidden="true" />Bỏ mục tiêu</button></div>}</td>
        </tr>)}</tbody>
      </table>}
      {d.goals.length < 10 && <div className="formgrid">
        <label className="field">Tên mục tiêu<input value={name} maxLength={80} disabled={busy} onChange={(e) => setName(e.target.value)} /></label>
        <label className="field">Số tiền (đ)<input inputMode="numeric" value={amount} disabled={busy} onChange={(e) => setAmount(groupDigitsInput(e.target.value))} /></label>
        <label className="field">Đếm theo<select value={basis} disabled={busy} onChange={(e) => setBasis(e.target.value as "value" | "gain")}>
          <option value="value">Giá trị danh mục</option><option value="gain">Lãi chưa chốt của danh mục</option></select></label>
      </div>}
      {d.goals.length < 10 && <div className="actions"><button className="btn primary" disabled={busy} onClick={() => void add()}><Plus size={16} aria-hidden="true" />Thêm mục tiêu</button></div>}
      {message && <p className="caption" role="status">{message}</p>}
    </div>
  );
}

/** Lãi đã trả lại thị trường and Mục tiêu đã đủ tiền: figures that already happened, never advice. */
export function GivebackView() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Data>("giveback").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const t = d?.thresholds;
  const p = d?.portfolio;
  return (
    <section className="surface" aria-label="Lãi đã trả lại thị trường">
      <h2>Lãi đã trả lại thị trường</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!d && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {d && p && t && <>
        <p className="caption">Lãi cao nhất mỗi mã đã có trong đợt nắm hiện tại, lãi hôm nay và phần đã trả lại. Tính trên giá điều chỉnh nên gồm cả cổ tức và
          cổ phiếu thưởng đã nhận; có thể khác cột lãi chưa chốt của bảng danh mục. {t.min_gain && t.share
            ? `Nhắc qua Telegram một lần khi một mã từng lãi từ ${formatRatio(t.min_gain, 0)} và đã trả lại từ ${formatRatio(t.share, 0)} lãi đó (sửa trong Cài đặt).`
            : "Mức chung chưa đặt: đặt hai ngưỡng trong Cài đặt nếu muốn được nhắc."} Giỏ chiến lược có thể đặt ngưỡng riêng hoặc không nhắc; ngưỡng
          đang áp ghi dưới từng mã. Chỉ là số đã xảy ra, không phải khuyến nghị.</p>
        {d.rows.length === 0 ? <p className="muted">Chưa có cổ phiếu đang nắm.</p> : <>
          <table className="fv-table cc-table" aria-label="Lãi đã trả lại theo mã">
            <thead><tr><th>Mã</th><th>Lãi cao nhất</th><th className="num">Lãi hôm nay</th><th>Đã trả lại</th><th /></tr></thead>
            <tbody>{[...d.rows].sort(byGivenBack).map((r) => <tr key={r.symbol}>
              <td data-label="Mã"><strong>{r.symbol}</strong><div className="caption">nắm từ {day(r.since)}</div>
                {r.rule && <div className="caption">ngưỡng {ruleLabel(r.rule)}</div>}</td>
              <td data-label="Lãi cao nhất">{peakLine(r)}</td>
              <td data-label="Lãi hôm nay" className="num">{r.now ? <>{formatVnd(r.now.gain)}{r.now.ratio && <div className="caption">{signed(r.now.ratio)} · {day(r.now.on)}</div>}</> : "—"}</td>
              <td data-label="Đã trả lại">{backLine(r)}</td>
              <td><Spark values={r.days.map((x) => Number(x.gain))} /></td>
            </tr>)}</tbody>
          </table>
          <p><strong>Cả danh mục:</strong> {p.missing.length > 0 ? `chưa tính được vì thiếu giá của ${p.missing.join(", ")}.`
            : <>lãi cao nhất {peakLine({ ...p, reason: null })}; hôm nay {p.now ? formatVnd(p.now.gain) : "—"}; đã trả lại {backLine(p)}.</>}</p>
          <p className="caption">Cộng lãi từng ngày của các mã đang nắm hôm nay, chỉ những ngày mã nào cũng có giá{p.skipped ? ` (bỏ ${p.skipped} ngày thiếu giá)` : ""}.
            Lãi đã chốt của mã đã bán không tính vào đây.</p>
        </>}
        <Goals d={d} onSaved={setD} />
      </>}
    </section>
  );
}
