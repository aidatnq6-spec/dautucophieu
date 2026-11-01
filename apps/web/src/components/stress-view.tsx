"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";

type Row = { symbol: string; shares: number; price: string | null; value: string | null; cost: string | null; beta: string | null;
  oil: string | null; usd: string | null; oil_note: string | null; usd_note: string | null };
type Preset = { id: string; label: string; market: string; oil: string; usd: string };
type Tolerance = { answer: string; limit: string | null; label: string };
type Data = { rows: Row[]; presets: Preset[]; worst: { depth: string; peak: string; trough: string } | null; tolerance: Tolerance | null; threshold: string };
type Shock = { market: number; oil: number; usd: number };
type Priced = { symbol: string; value: number; move: number; change: number; notes: string[]; crossesThreshold: boolean };

const round = (x: number) => Math.round(x * 1e6) / 1e6;

/** A shock applied to each holding: beta × the VN-Index move, plus the oil and US-dollar relations where they are clear. Holdings
 * without a price, or without a beta when the VN-Index moves, are left out and named; an unclear factor is noted as not counted. */
export function applyScenario(inputs: { rows: Row[]; threshold: string; tolerance: Tolerance | null }, shock: Shock) {
  const rows: Priced[] = [];
  const excluded: { symbol: string; reason: string }[] = [];
  for (const r of inputs.rows) {
    if (r.value === null || r.price === null) { excluded.push({ symbol: r.symbol, reason: "Chưa có giá" }); continue; }
    if (shock.market !== 0 && r.beta === null) { excluded.push({ symbol: r.symbol, reason: "Thiếu beta (VNDirect)" }); continue; }
    const notes: string[] = [];
    let move = shock.market !== 0 ? Number(r.beta) * shock.market : 0;
    for (const [key, label, coeff, why] of [["oil", "Dầu", r.oil, r.oil_note], ["usd", "Đồng USD", r.usd, r.usd_note]] as const) {
      const size = shock[key];
      if (size === 0) continue;
      if (coeff === null) notes.push(`${label}: chưa tính (${why ?? "không có số"})`);
      else move += Number(coeff) * size;
    }
    move = round(move);
    const value = Number(r.value), price = Number(r.price), cost = r.cost === null ? null : Number(r.cost);
    const threshold = Number(inputs.threshold);
    const after = price * (1 + move);
    const crossesThreshold = cost !== null && cost > 0 && price / cost - 1 > -threshold && after / cost - 1 <= -threshold;
    rows.push({ symbol: r.symbol, value, move, change: Math.round(value * move), notes, crossesThreshold });
  }
  const counted = rows.reduce((a, r) => a + r.value, 0);
  const total = rows.reduce((a, r) => a + r.change, 0);
  const pct = counted > 0 ? total / counted : null;
  const limit = inputs.tolerance?.limit;
  return { rows, excluded, total, pct, counted, overTolerance: limit && pct !== null ? pct <= -Number(limit) : null };
}

const pctText = (x: number) => `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
const vnd = (x: number) => (x < 0 ? "−" : "") + formatVnd(String(Math.abs(x)));
const input = (raw: string) => { const v = Number(raw.trim().replace(",", ".")); return Number.isFinite(v) ? v / 100 : null; };

/** Kiểm tra sức chịu đựng: a shock on the VN-Index, oil or the US dollar priced on the holdings — a linear estimate from past relations. */
export function StressView() {
  const [data, setData] = useState<Data | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [fields, setFields] = useState({ market: "-20", oil: "0", usd: "0" });
  useEffect(() => { api<Data>("stress").then(setData, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const shock = { market: input(fields.market), oil: input(fields.oil), usd: input(fields.usd) };
  const ready = shock.market !== null && shock.oil !== null && shock.usd !== null;
  const out = data && ready ? applyScenario(data, shock as Shock) : null;
  const pick = (p: Preset) => setFields({ market: String(Number(p.market) * 100), oil: String(Number(p.oil) * 100), usd: String(Number(p.usd) * 100) });
  return (
    <section className="surface" aria-label="Kiểm tra sức chịu đựng">
      <h2>Kiểm tra sức chịu đựng</h2>
      <p className="caption">Ước tính tuyến tính từ quan hệ trong quá khứ, không phải dự báo: mỗi mã thay đổi = beta (VNDirect) × thay đổi VN-Index, cộng hệ số
        dầu và đồng USD (chỉ số rộng, không phải tỷ giá USD/VND) khi quan hệ 3 năm qua là rõ (trang Vĩ mô). Không có kịch bản lãi suất vì chưa đo
        được quan hệ giữa lãi suất và giá từng mã. Không phải khuyến nghị.</p>
      {message && <p className="errors" role="alert">{message}</p>}
      {!data && !message && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {data && (data.rows.length === 0 ? <p className="muted">Chưa có cổ phiếu trong sổ.</p> : <>
        <div className="sc-saved" role="group" aria-label="Kịch bản có sẵn">
          {data.presets.map((p) => <button key={p.id} type="button" className="btn" onClick={() => pick(p)}>{p.label}</button>)}
        </div>
        <div className="st-inputs">
          {([["market", "VN-Index (%)"], ["oil", "Giá dầu (%)"], ["usd", "Đồng USD (%)"]] as const).map(([k, label]) => <label key={k} className="field">{label}
            <input inputMode="decimal" value={fields[k]} onChange={(e) => setFields({ ...fields, [k]: e.target.value })} /></label>)}
        </div>
        {!ready && <p className="notice">Nhập số phần trăm, ví dụ −20 hoặc 30.</p>}
        {out && <>
          <p data-testid="stress-total"><strong>Danh mục cổ phiếu: {vnd(out.total)}{out.pct !== null && ` (${pctText(out.pct)})`}</strong>
            {" "}trên {formatVnd(String(out.counted))} được tính.</p>
          {data.tolerance ? <p className={out.overTolerance ? "notice" : "caption"} data-testid="stress-tolerance">{data.tolerance.limit === null
            ? `Bạn khai chịu được ${data.tolerance.label.toLowerCase()} (câu 10 khảo sát rủi ro): không có giới hạn trên để so.`
            : out.overTolerance ? `Vượt mức bạn khai chịu được (${data.tolerance.label.toLowerCase()}, câu 10 khảo sát rủi ro).`
              : `Chưa vượt mức bạn khai chịu được (${data.tolerance.label.toLowerCase()}, câu 10 khảo sát rủi ro).`}</p>
            : <p className="caption">Chưa có khảo sát rủi ro để so mức chịu đựng.</p>}
          <div className="tablewrap"><table aria-label="Kịch bản theo mã">
            <thead><tr><th>Mã</th><th className="num">Giá trị hiện tại</th><th className="num">Thay đổi ước tính</th><th className="num">Số tiền</th><th>Ghi chú</th></tr></thead>
            <tbody>{out.rows.map((r) => <tr key={r.symbol}><td><strong>{r.symbol}</strong></td><td className="num">{formatVnd(String(r.value))}</td>
              <td className="num">{pctText(r.move)}</td><td className="num">{vnd(r.change)}</td>
              <td className="wrap">{[r.crossesThreshold ? `Sẽ thấp hơn giá vốn quá ${pctText(-Number(data.threshold)).replace("−", "")} (Kế hoạch sụt giảm)` : "",
                ...r.notes].filter(Boolean).join("; ")}</td></tr>)}</tbody>
          </table></div>
          {out.excluded.length > 0 && <p className="caption" data-testid="stress-excluded">Không tính: {out.excluded.map((e) => `${e.symbol} (${e.reason})`).join(", ")}.</p>}
        </>}
      </>)}
    </section>
  );
}
