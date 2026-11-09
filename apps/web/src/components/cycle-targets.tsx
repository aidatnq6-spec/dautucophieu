"use client";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, parseMoneyInput } from "../lib/format";

const LAYERS = [["deposit", "Tiền gửi"], ["bond", "Trái phiếu"], ["gold", "Vàng"], ["stocks", "Cổ phiếu"], ["crypto", "Tiền số"]] as const;
const PHASES = [["up", "Lãi suất tăng"], ["down", "Lãi suất giảm"], ["flat", "Lãi suất đi ngang"]] as const;
type Layer = (typeof LAYERS)[number][0];
type Phase = (typeof PHASES)[number][0];
type Mix = Record<Layer, string>;
type Row = { id: Layer; held: string; share: string | null; target: string; gap: string | null };
type View = { version: number; targets: Record<Phase, Mix | null>; phase: Phase | null; basis: "vietnam" | "us_reference" | null; reason: string | null; rows: Row[] };
type Grid = Record<Phase, Record<Layer, string>>;

const REASON: Record<string, string> = { no_phase: "Chưa đủ dữ liệu để đọc giai đoạn lãi suất, nên chưa so được.", no_total: "Chưa có Tháp tài sản: nhập Sổ tài sản hoặc các lớp bên trên.",
  no_risk: "Tháp tài sản chưa tính được vì chưa có nhóm rủi ro.", no_layers: "Tháp tài sản đang dùng một con số tổng, chưa có từng lớp để so.", no_target: "Chưa đặt mục tiêu cho giai đoạn này." };
const NAME = Object.fromEntries(LAYERS) as Record<Layer, string>;

function toGrid(targets: View["targets"]): Grid {
  const grid = {} as Grid;
  for (const [phase] of PHASES) grid[phase] = Object.fromEntries(LAYERS.map(([l]) => [l, targets[phase]?.[l]?.replace(".", ",") ?? ""])) as Record<Layer, string>;
  return grid;
}

/** Each phase's mix to the API's shape: a row left blank is unset; a row part filled, unreadable or not at 100% is refused with its name. */
export function gridPayload(grid: Grid): { ok: Record<Phase, Mix | null> } | { error: string } {
  const ok = {} as Record<Phase, Mix | null>;
  for (const [phase, title] of PHASES) {
    const cells = LAYERS.map(([l]) => grid[phase][l].trim());
    if (cells.every((c) => c === "")) { ok[phase] = null; continue; }
    const values = cells.map((c) => parseMoneyInput(c));
    if (values.some((v) => v === null)) return { error: `${title}: nhập đủ 5 lớp bằng số, lớp không có thì ghi 0.` };
    const hundredths = values.reduce((sum, v) => sum + Math.round(Number(v) * 100), 0);
    if (hundredths !== 10000) return { error: `${title}: tổng đang là ${String(hundredths / 100).replace(".", ",")}%, cần đúng 100%.` };
    ok[phase] = Object.fromEntries(LAYERS.map(([l], i) => [l, values[i]])) as Mix;
  }
  return { ok };
}

/** Phân bổ mục tiêu theo chu kỳ: the owner's own mix for each phase of rates, and how far the layers held now are from the current phase's. Suggests nothing. */
export function CycleTargets({ refresh }: { refresh?: string } = {}) {
  const [view, setView] = useState<View | null>(null);
  const [grid, setGrid] = useState<Grid | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const fail = (e: unknown, fallback: string) => setError(e instanceof ApiError ? e.failure.message : fallback);
  // A change elsewhere on the page reloads the comparison; what is being typed in the grid stays.
  useEffect(() => { api<View>("cycle-targets").then((v) => { setView(v); setGrid((current) => current ?? toGrid(v.targets)); }, (e) => fail(e, "Lỗi tải.")); }, [refresh]);
  async function save() {
    if (!view || !grid) return;
    setSaved(false);
    const r = gridPayload(grid);
    if ("error" in r) { setError(r.error); return; }
    setBusy(true); setError(null);
    try {
      const next = await api<View>("cycle-targets", { method: "PUT", body: { ...r.ok, expected_version: view.version, request_id: requestId() } });
      setView(next); setGrid(toGrid(next.targets)); setSaved(true);
    } catch (e) { fail(e, "Lỗi lưu."); } finally { setBusy(false); }
  }
  const phaseName = view?.phase ? PHASES.find(([p]) => p === view.phase)![1] : null;
  return (
    <section className="surface" aria-label="Phân bổ mục tiêu theo chu kỳ">
      <h2>Phân bổ mục tiêu theo chu kỳ</h2>
      <p className="caption wrap">Bạn tự đặt tỷ trọng mong muốn cho từng giai đoạn lãi suất, phần mềm so với các lớp đang có. Tỷ trọng tính trên phần sau quỹ dự phòng, tiền gửi gồm cả tiền mặt, cổ phiếu theo giá vốn như Tháp. Không ảnh hưởng mục tiêu của Tháp hay phần chia tiền mới. Phép so trên số bạn đặt, không phải dự báo hay khuyến nghị.</p>
      {view && phaseName && <p><strong>Giai đoạn hiện tại: {phaseName.toLowerCase()}</strong>{view.basis === "us_reference" ? " (tạm theo lãi suất Mỹ, chưa đủ dữ liệu Việt Nam)" : ""}, theo Mốc chu kỳ lãi suất ở trang Vĩ mô.</p>}
      {view?.reason && <p className="notice pv-note" data-testid="ct-reason">{REASON[view.reason]}</p>}
      {view && view.rows.length > 0 && <div className="tablewrap"><table aria-label="Chênh lệch so với mục tiêu của giai đoạn">
        <thead><tr><th>Lớp</th><th className="num">Đang có</th><th className="num">Tỷ trọng</th><th className="num">Mục tiêu</th><th className="num">Chênh lệch</th></tr></thead>
        <tbody>{view.rows.map((r) => <tr key={r.id}><td>{NAME[r.id]}</td><td className="num">{formatVnd(r.held)}</td><td className="num">{r.share === null ? "—" : formatRatio(r.share, 1)}</td><td className="num">{formatRatio(r.target, 1)}</td>
          <td className="num" data-testid={`ct-gap-${r.id}`}>{r.gap === null ? "—" : r.gap === "0" ? "đúng mục tiêu" : Number(r.gap) > 0 ? `thiếu ${formatVnd(r.gap)}` : `vượt ${formatVnd(r.gap.slice(1))}`}</td></tr>)}</tbody>
      </table></div>}
      <h3>Mục tiêu của bạn (%)</h3>
      {grid && <form onSubmit={(e) => { e.preventDefault(); void save(); }}>
        {PHASES.map(([phase, title]) => <fieldset key={phase}><legend>{title}{view?.phase === phase ? " · đang ở giai đoạn này" : ""}</legend>
          <div className="ct-row">{LAYERS.map(([l, name]) => <label key={l} className="field">{name}<input inputMode="decimal" aria-label={`${title}: ${name} (%)`} value={grid[phase][l]}
            onChange={(e) => { setSaved(false); setGrid({ ...grid, [phase]: { ...grid[phase], [l]: e.target.value } }); }} /></label>)}</div></fieldset>)}
        {error && <p className="errors" role="alert">{error}</p>}
        <div className="actions"><button type="submit" className="btn primary" disabled={busy}>Lưu mục tiêu</button>{saved && <span role="status" className="caption">Đã lưu.</span>}</div>
      </form>}
      {!grid && error && <p className="errors" role="alert">{error}</p>}
    </section>
  );
}
