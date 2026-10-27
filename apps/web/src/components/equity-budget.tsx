"use client";
import { useEffect, useState } from "react";
import { Calculator } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd, groupDigitsInput, parseMoneyInput } from "../lib/format";
import { GROUP_LABEL } from "./risk-survey";
import type { IntangiblesView } from "./intangibles";

type Layer = { id: string; amount: string; share: string | null; target_min: string | null; target_max: string | null;
  status: "fixed" | "short" | "ok" | "over"; gap: string | null };
type Funding = { sources: { id: string; surplus: string }[]; pool: string; fills: { id: string; amount: string }[]; left_for_stocks: string;
  stock_room: string; buyable: string; from_cash: string; to_raise: string };
type Pyramid = { total: string; base: string; layers: Layer[]; warnings: { short: string; over: string[] }[]; funding?: Funding };
type Layers = { deposit: string; bond: string; gold: string; crypto: string };
type Budget = { status: "no_total" | "no_risk" | "ok"; total?: string; deductions?: string; base?: string; group?: string; ratio?: string;
  budget?: string; held_cost?: string; held_weight?: string | null; room?: string | null; over?: string | null;
  deductions_source?: "manual" | "profile"; profile_deductions?: string; reserve?: string | null; layers?: Layers | null; pyramid?: Pyramid | null };
type View = { version: number; budget: Budget };

const pct = (r: string) => formatRatio(r, 1).replace(",0%", "%");
const whole = (r: string) => formatRatio(r, 1).replace(",0%", "").replace("%", "");
const NAME: Record<string, string> = { reserve: "Dự phòng", cash: "Tiền mặt", deposit: "Tiền gửi", bond: "Trái phiếu", gold: "Vàng", stocks: "Cổ phiếu", crypto: "Tiền số" };
const NOTE: Record<string, string> = { reserve: "quỹ dự phòng và khoản chi 12 tháng", cash: "trong tài khoản chứng khoán, lấy từ sổ giao dịch",
  deposit: "% và mục tiêu tính cùng tiền mặt",
  stocks: "theo giá mua, từ sổ giao dịch" };
const STATUS: Record<string, [string, string]> = { short: ["thiếu", "warn"], ok: ["đủ", "good"], over: ["vượt", "bad"], fixed: ["cố định", ""],
  with_deposit: ["tính chung mục tiêu với tiền gửi", ""] };
const INPUTS: [keyof Layers, string][] = [["deposit", "Tiền gửi (đ)"], ["bond", "Trái phiếu (đ)"], ["gold", "Vàng (đ)"], ["crypto", "Tiền số (đ)"]];

function target(l: Layer) {
  if (l.target_min === null || l.target_max === null) return "";
  if (l.target_min === "0") return `mục tiêu tối đa ${pct(l.target_max)}`;
  return `mục tiêu ${whole(l.target_min)}–${pct(l.target_max)}`;
}

/** Tháp tài sản: layers from the bottom up against their targets, the total they add up to, and the money for stocks it gives. */
function PyramidView({ p, intangibles }: { p: Pyramid; intangibles: IntangiblesView["year"] | null }) {
  return (
    <>
      <ol className="pyr" aria-label="Các lớp tài sản, từ dưới lên">
        {p.layers.map((l, i) => {
          const [word, tone] = STATUS[l.status];
          return (
            <li key={l.id} data-testid={`layer-${l.id}`} className={`pyr-layer pyr-${l.status}`} style={{ ["--step" as string]: i }}>
              <div className="pyr-name"><strong>{NAME[l.id]}</strong>{NOTE[l.id] && <span className="caption"> · {NOTE[l.id]}</span>}</div>
              <div className="pyr-figs">
                <span>{formatVnd(l.amount)}</span>
                {l.share !== null && <span>{pct(l.share)}</span>}
                <span className="caption">{target(l)}</span>
                <span className={`pill ${tone}`}>{word}{l.gap ? ` ${formatVnd(l.gap)}` : ""}</span>
              </div>
            </li>
          );
        })}
        {intangibles && <li className="pyr-layer pyr-intangible" data-testid="pyramid-intangibles" style={{ ["--step" as string]: -1 }}>
          <div className="pyr-name"><strong>Tài sản vô hình: năm nay {formatVnd(intangibles.spent)}</strong>
            <span className="caption"> · đế của tháp, đầu tư vào bản thân; không tính vào tổng tài sản</span></div>
        </li>}
      </ol>
      {p.warnings.map((w) => {
        const short = p.layers.find((l) => l.id === w.short)!;
        return <p key={w.short} className="notice">{NAME[w.short]} đang thiếu {formatVnd(short.gap)} trong khi {w.over.map((o) => NAME[o]).join(", ")} đã
          vượt mục tiêu: theo nguyên tắc tháp tài sản, nên bổ sung lớp dưới trước.</p>;
      })}
    </>
  );
}

const SOURCE: Record<string, string> = { deposit: "Tiền gửi + tiền mặt", bond: "Trái phiếu", gold: "Vàng", crypto: "Tiền số" };

/** Where more money for stocks could come from: what sits above each layer's ceiling, after filling layers below their minimum first
 * (the owner's rule). A calculation on the owner's figures, not advice; never from a short layer or the reserve. */
function FundingView({ f }: { f: Funding }) {
  return (
    <section className="eb-funding" aria-label="Nguồn tiền để mua thêm cổ phiếu">
      <h3>Nguồn tiền để mua thêm cổ phiếu</h3>
      <p className="caption">Chỉ lấy phần vượt mức trần của từng lớp; phần này bù các lớp đang dưới mức tối thiểu trước, còn lại mới dành cho cổ phiếu.
        Không lấy từ lớp đang thiếu hay quỹ dự phòng. Phép tính trên số bạn nhập, không phải khuyến nghị.</p>
      <dl className="eb-result">
        {f.sources.map((s) => <div key={s.id} data-testid={`funding-source-${s.id}`}><dt>{SOURCE[s.id]} <span className="caption">(phần vượt mức trần)</span></dt>
          <dd>{s.surplus === "0" ? <span className="muted">0 đ · không lấy</span> : formatVnd(s.surplus)}</dd></div>)}
        <div><dt>Tổng phần dư</dt><dd>{formatVnd(f.pool)}</dd></div>
        {f.fills.map((x) => <div key={x.id} data-testid={`funding-fill-${x.id}`}><dt>Bù {NAME[x.id].toLowerCase()} lên mức tối thiểu trước</dt>
          <dd>−{formatVnd(x.amount)}</dd></div>)}
        <div><dt>Còn lại cho cổ phiếu</dt><dd>{formatVnd(f.left_for_stocks)}</dd></div>
        <div><dt>Còn trống trong vốn dành cho cổ phiếu</dt><dd data-testid="funding-room">{formatVnd(f.stock_room)}</dd></div>
        <div className="eb-main"><dt>Có thể mua thêm <span className="caption">(số nhỏ hơn của hai dòng trên)</span></dt>
          <dd data-testid="funding-buyable">{formatVnd(f.buyable)}</dd></div>
        {f.buyable !== "0" && <div><dt>Trong đó</dt><dd>tiền mặt sẵn trong tài khoản {formatVnd(f.from_cash)} · cần rút hoặc bán thêm {formatVnd(f.to_raise)}</dd></div>}
      </dl>
    </section>
  );
}

/** Layers of financial assets → total → money for stocks by risk group. Holdings at cost; an excess is shown, never a sell. */
export function EquityBudget() {
  const [view, setView] = useState<View | null>(null);
  const [values, setValues] = useState<Layers>({ deposit: "", bond: "", gold: "", crypto: "" });
  const [reserve, setReserve] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [intangibles, setIntangibles] = useState<IntangiblesView["year"] | null>(null);
  useEffect(() => { api<IntangiblesView>("intangibles").then((v) => setIntangibles(v.year), () => setIntangibles(null)); }, []);
  useEffect(() => {
    api<View>("equity-budget").then((v) => {
      setView(v);
      const l = v.budget.layers;
      if (l) setValues({ deposit: formatVnd(l.deposit, { unit: false }), bond: formatVnd(l.bond, { unit: false }), gold: formatVnd(l.gold, { unit: false }),
        crypto: formatVnd(l.crypto, { unit: false }) });
      if (v.budget.reserve) setReserve(formatVnd(v.budget.reserve, { unit: false }));
    }, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  async function save() {
    if (!view) return;
    const layers = Object.fromEntries(INPUTS.map(([k]) => [k, values[k].trim() ? parseMoneyInput(values[k]) : "0"])) as Record<keyof Layers, string | null>;
    if (Object.values(layers).some((v) => v === null || v.includes("."))) { setMessage("Nhập số đồng cho từng lớp, ví dụ 200.000.000 (để trống = 0)."); return; }
    const manual = reserve.trim() ? parseMoneyInput(reserve) : null;  // empty = use the profile's figure
    if (reserve.trim() && (manual === null || manual.includes("."))) { setMessage("Quỹ dự phòng: nhập số đồng, hoặc để trống."); return; }
    try {
      setView(await api<View>("equity-budget", { method: "PUT", body: { layers, reserve: manual, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const b = view?.budget;
  return (
    <section className="surface" aria-label="Tháp tài sản">
      <h2>Tháp tài sản</h2>
      <p className="caption">Nhập số tiền bạn đang có ở từng lớp; cổ phiếu (theo giá mua) và tiền mặt trong tài khoản chứng khoán lấy từ sổ giao dịch
        (tiền mặt tính chung mục tiêu với tiền gửi).
        Tổng tài sản là tổng các lớp. Mục tiêu tính trên phần còn lại sau quỹ dự phòng: vàng 10–15%, trái phiếu tối đa 10%, cổ phiếu theo khẩu vị,
        tiền số tối đa 5%, tiền gửi là phần còn lại. Xây từ dưới lên. Trang Danh mục tính tỷ trọng từng mã trên vốn dành cho cổ phiếu.</p>
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
        {INPUTS.map(([k, label]) => <label key={k} className="field">{label}<input inputMode="numeric" value={values[k]} disabled={!view}
          onChange={(e) => setValues({ ...values, [k]: groupDigitsInput(e.target.value) })} /></label>)}
        <label className="field">Quỹ dự phòng và khoản chi 12 tháng (đ)<input inputMode="numeric" value={reserve} disabled={!view}
          onChange={(e) => setReserve(groupDigitsInput(e.target.value))}
          placeholder={b?.profile_deductions ? `để trống = theo hồ sơ (${formatVnd(b.profile_deductions)})` : "để trống = theo hồ sơ"} /></label>
        <button type="submit" className="btn primary" disabled={!view}><Calculator size={16} aria-hidden="true" />Tính tháp tài sản</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {b?.status === "ok" && !b.pyramid && <p className="notice">Đang dùng tổng tài sản nhập một con số ({formatVnd(b.total)}). Nhập số tiền từng lớp ở trên để xem tháp tài sản.</p>}
      {b?.status === "no_risk" && <p className="notice">Chưa có kết quả khảo sát rủi ro nên chưa biết tỷ trọng cổ phiếu.</p>}
      {b?.status === "ok" && b.pyramid && <PyramidView p={b.pyramid} intangibles={intangibles} />}
      {b?.status === "ok" && <dl className="eb-result">
        <div><dt>Tổng tài sản tài chính</dt><dd data-testid="equity-total">{formatVnd(b.total)}</dd></div>
        <div><dt>Trừ quỹ dự phòng và khoản chi 12 tháng <span className="caption">({b.deductions_source === "manual" ? "nhập tay" : "theo hồ sơ"})</span></dt>
          <dd data-testid="equity-deductions">{b.deductions === "0" ? "0 đ" : `−${formatVnd(b.deductions)}`}</dd></div>
        <div><dt>Nhóm khẩu vị</dt><dd>{GROUP_LABEL[b.group!] ?? b.group} → tỷ trọng cổ phiếu {pct(b.ratio!)}</dd></div>
        <div className="eb-main"><dt>Vốn dành cho cổ phiếu</dt><dd data-testid="equity-budget">{formatVnd(b.budget)}</dd></div>
        <div><dt>Đang nắm (theo giá mua): {formatVnd(b.held_cost)}{b.held_weight ? ` (${pct(b.held_weight)})` : ""}</dt>
          <dd>{b.over ? <span className="negative">Đã vượt {formatVnd(b.over)}</span> : <>còn trống {formatVnd(b.room)}</>}</dd></div>
      </dl>}
      {b?.status === "ok" && b.pyramid?.funding && <FundingView f={b.pyramid.funding} />}
    </section>
  );
}
