"use client";
import { useEffect, useState } from "react";
import { Calculator } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

type Band = { k: number; multiple: string | null; price: string | null; gap: string | null };
type Year = { year: string; eps: string; bvps: string; pe: Band[]; pb: Band[]; custom?: { pe: string | null; pb: string | null } };
type Assumptions = { profit_growth: string[]; equity_growth: string[]; dilution: string[] };
type View = { symbol: string; version: number; assumptions: Assumptions | null; custom: { pe?: string; pb?: string }; reason: string | null;
  notes: string[]; base: { year: string; eps: string; bvps: string; price: string | null } | null; years: Year[] };

const ROWS = 3;
const toPct = (v: string | undefined) => (v === undefined ? "" : String(Math.round(Number(v) * 10000) / 100).replace(".", ","));
const fromPct = (v: string) => { const n = Number(v.trim().replace(",", ".")); return Number.isFinite(n) ? String(n / 100) : null; };
const kLabel = (k: number) => (k === 0 ? "Trung vị" : `${k > 0 ? "+" : "−"}${Math.abs(k)} ĐLC`);
const gapText = (g: string | null) => (g === null ? "—" : `${g.startsWith("-") ? "" : "+"}${formatRatio(g, 1)}`);

/** The owner's growth scenario for one to three years, priced on the ticker's own P/E and P/B bands (±1, 2, 3 SD). */
export function ForwardValuation({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [grid, setGrid] = useState<string[][]>(() => Array.from({ length: ROWS }, () => ["", "", ""]));
  const [pe, setPe] = useState("");
  const [pb, setPb] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  function load(v: View) {
    setView(v);
    const a = v.assumptions;
    if (a) setGrid(Array.from({ length: ROWS }, (_, i) => [toPct(a.profit_growth[i]), toPct(a.equity_growth[i]), toPct(a.dilution[i])]));
    setPe((v.custom.pe ?? "").replace(".", ",")); setPb((v.custom.pb ?? "").replace(".", ","));
  }
  useEffect(() => { api<View>(`fairvalue/forward/${encodeURIComponent(symbol)}`).then(load, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [symbol]);

  async function save() {
    if (!view) return;
    const filled = grid.filter((r) => r.some((c) => c.trim()));
    if (filled.length === 0 || grid.slice(0, filled.length).some((r) => r[0].trim() === "" || r[1].trim() === "")) {
      setMessage("Nhập tăng trưởng lợi nhuận và vốn chủ từ năm thứ nhất, liền nhau (pha loãng để trống = 0%)."); return;
    }
    const rows = grid.slice(0, filled.length).map((r) => [fromPct(r[0]), fromPct(r[1]), r[2].trim() ? fromPct(r[2]) : "0"]);
    if (rows.some((r) => r.some((c) => c === null))) { setMessage("Các ô phải là số phần trăm, ví dụ 15 hoặc -5."); return; }
    try {
      load(await api<View>(`fairvalue/forward/${encodeURIComponent(symbol)}`, { method: "PUT", body: {
        assumptions: { profit_growth: rows.map((r) => r[0]), equity_growth: rows.map((r) => r[1]), dilution: rows.map((r) => r[2]) },
        custom: { pe: pe.trim().replace(",", ".") || null, pb: pb.trim().replace(",", ".") || null }, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  const base = view?.base;
  return (
    <section className="surface" aria-label="Định giá dự phóng">
      <h2>Định giá dự phóng</h2>
      <p className="caption">Kịch bản của bạn: tăng trưởng lợi nhuận công ty mẹ và vốn chủ mỗi năm (và pha loãng cổ phiếu nếu có). Giá = EPS (BVPS) dự phóng × P/E (P/B)
        trung vị của chính mã này ± 1, 2, 3 độ lệch chuẩn theo tháng (như biểu đồ). Không phải dự báo của phần mềm, không phải khuyến nghị.</p>
      {view?.reason && <p className="muted">{view.reason}.</p>}
      {base && <p>Năm gốc {base.year}: EPS {formatVnd(base.eps)} · BVPS {formatVnd(base.bvps)} · giá hiện tại {base.price ? formatVnd(base.price) : "—"}
        <span className="caption"> (chia cho số cổ phiếu hiện tại, đã gồm các đợt phát hành sau năm gốc, để so được với giá hôm nay)</span></p>}
      <form onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <table className="fv-table" aria-label="Giả định tăng trưởng">
          <thead><tr><th>Năm</th><th>Tăng trưởng lợi nhuận (%)</th><th>Tăng trưởng vốn chủ (%)</th><th>Pha loãng cổ phiếu (%)</th></tr></thead>
          <tbody>{grid.map((r, i) => <tr key={i}>
            <td data-label="Năm">{base ? Number(base.year) + i + 1 : `+${i + 1}`}</td>
            {["Tăng trưởng lợi nhuận", "Tăng trưởng vốn chủ", "Pha loãng cổ phiếu"].map((name, j) => <td key={name} data-label={name}>
              <input aria-label={`${name} năm ${i + 1}`} inputMode="decimal" value={r[j]} disabled={!view}
                onChange={(e) => setGrid(grid.map((row, a) => (a === i ? row.map((c, b) => (b === j ? e.target.value : c)) : row)))} /></td>)}
          </tr>)}</tbody>
        </table>
        <div className="fv-search">
          <label className="field">Giả sử P/E =<input inputMode="decimal" value={pe} disabled={!view} onChange={(e) => setPe(e.target.value)} /></label>
          <label className="field">Giả sử P/B =<input inputMode="decimal" value={pb} disabled={!view} onChange={(e) => setPb(e.target.value)} /></label>
          <button type="submit" className="btn primary" disabled={!view || !base}><Calculator size={16} aria-hidden="true" />Tính và lưu kịch bản</button>
        </div>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
      {view?.notes.map((n) => <p key={n} className="caption">{n}.</p>)}
      {view?.years.map((y) => (
        <div key={y.year}>
          <h3>Năm {y.year}: EPS {formatVnd(y.eps)} · BVPS {formatVnd(y.bvps)}</h3>
          {y.custom && (y.custom.pe || y.custom.pb) && <p>{y.custom.pe && <>Với P/E {pe}: <strong>{formatVnd(y.custom.pe)}</strong> </>}
            {y.custom.pb && <>Với P/B {pb}: <strong>{formatVnd(y.custom.pb)}</strong></>}</p>}
          <table className="fv-table" aria-label={`Giá dự phóng năm ${y.year}`}>
            <thead><tr><th>Mức</th><th className="num">P/E</th><th className="num">Giá theo P/E</th><th className="num">So với giá nay</th>
              <th className="num">P/B</th><th className="num">Giá theo P/B</th><th className="num">So với giá nay</th></tr></thead>
            <tbody>{[3, 2, 1, 0, -1, -2, -3].map((k) => {
              const a = y.pe.find((b) => b.k === k), b = y.pb.find((x) => x.k === k);
              return <tr key={k} className={k === 0 ? "fv-median" : undefined}><td data-label="Mức">{kLabel(k)}</td>
                <td data-label="P/E" className="num">{a?.multiple ? formatDecimal(a.multiple, 2) : "—"}</td>
                <td data-label="Giá theo P/E" className="num">{a?.price ? formatVnd(a.price) : "—"}</td>
                <td data-label="So với giá nay" className="num">{gapText(a?.gap ?? null)}</td>
                <td data-label="P/B" className="num">{b?.multiple ? formatDecimal(b.multiple, 2) : "—"}</td>
                <td data-label="Giá theo P/B" className="num">{b?.price ? formatVnd(b.price) : "—"}</td>
                <td data-label="So với giá nay" className="num">{gapText(b?.gap ?? null)}</td></tr>;
            })}</tbody>
          </table>
        </div>))}
    </section>
  );
}
