"use client";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";

export type RrRow = { name: string; amount: string; grouped: boolean; related: boolean; secured: boolean | null; interest: boolean | null;
  collect_within: string | null; kind?: RrKind | null; rate?: string | null; accrued_interest?: string | null };
export type RrKind = "customer" | "prepay" | "other" | "loan";
export const KIND: Record<RrKind, string> = { customer: "Phải thu khách hàng", prepay: "Trả trước người bán", other: "Phải thu khác", loan: "Cho vay" };
type Year = { year: string; source: string; rows: RrRow[]; related_total: string; named_related: string; accrued_interest?: string | null };
export type Finding =
  | { kind: "vanished"; year: string; from_year: string; name: string; amount: string; row_kind?: RrKind | null; group: { name: string; amount: string } | null }
  | { kind: "not_collected"; year: string; name: string; before: string; now: string; promised: string }
  | { kind: "unsecured_free"; year: string; name: string; amount: string }
  | { kind: "interest_piling"; year: string; name: string; before: string; now: string; rate: string | null };
type View = { symbol: string; version: number; years: Year[]; findings: Finding[] };
type Proposal = { status: "ok" | "unverified" | "no_passages"; reason?: string; rows: (RrRow & { page: number })[];
  dropped: { name: string; reason: string }[]; url: string; cost_usd: string };
const DROPPED: Record<string, string> = { amount_not_on_page: "số dư không có trên trang AI ghi", page_not_sent: "trang không thuộc phần đã đọc",
  no_name: "thiếu tên" };

/** The note after an AI proposal: what was filled in and what was left out, and why. */
export function proposalNote(p: Proposal): string {
  if (p.status === "no_passages") return "Tài liệu không có đoạn nào về phải thu bên liên quan; chưa gửi gì cho AI.";
  if (p.status === "unverified") return "AI không ghi đúng đơn vị tính của tài liệu, nên không điền gì.";
  const kept = p.rows.length ? `Đã điền ${p.rows.length} dòng (trang ${[...new Set(p.rows.map((r) => r.page))].join(", ")}): đọc lại từng dòng rồi mới lưu.` : "AI không tìm thấy khoản nào.";
  const left = p.dropped.length ? ` Bỏ ${p.dropped.length} dòng: ${p.dropped.map((d) => `${d.name || "—"} (${DROPPED[d.reason] ?? d.reason})`).join("; ")}.` : "";
  return `${kept}${left} Chi phí ${p.cost_usd} USD.`;
}

type Draft = { name: string; amount: string; grouped: boolean; related: boolean; secured: "" | "yes" | "no"; interest: "" | "yes" | "no"; collect_within: string;
  kind: "" | RrKind; rate: string; accrued_interest: string };

export const ty = (v: string) => `${Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tỷ`;
const tri = (v: boolean | null) => (v === null ? "—" : v ? "có" : "không");
const EMPTY: Draft = { name: "", amount: "", grouped: false, related: true, secured: "", interest: "", collect_within: "", kind: "", rate: "", accrued_interest: "" };

/** One finding in words. */
export function findingText(f: Finding): string {
  if (f.kind === "vanished") {
    const what = f.row_kind === "prepay" ? " (nhà cung cấp được nêu tên trong thuyết minh trả trước)" : "";
    return `${f.name}${what} (${ty(f.amount)} năm ${f.from_year}) không còn được nêu tên năm ${f.year}`
      + (f.group ? `; có thể đã nằm trong dòng gộp "${f.group.name}" (${ty(f.group.amount)}).` : ".")
      + " Đọc thuyết minh năm trước để biết đối tượng và hỏi khoản này đã thu chưa.";
  }
  if (f.kind === "not_collected") {
    return `${f.name}: hứa thu trong ${f.promised}, nhưng năm ${f.year} vẫn còn ${ty(f.now)} (năm trước ${ty(f.before)}).`;
  }
  if (f.kind === "interest_piling") {
    return `${f.name}: lãi cho vay phải thu tăng từ ${ty(f.before)} lên ${ty(f.now)} năm ${f.year}${f.rate ? ` (lãi suất ${f.rate})` : ""}. `
      + "Lãi được ghi vào doanh thu tài chính nhưng chưa thu được tiền: lợi nhuận \"giấy\", có thể phải trích dự phòng sau này.";
  }
  return `${f.name}: phải thu bên liên quan ${ty(f.amount)} năm ${f.year}, không có bảo đảm và không tính lãi.`;
}

const toDraft = (r: RrRow): Draft => ({ name: r.name, amount: r.amount.replace(".", ","), grouped: r.grouped, related: r.related,
  secured: r.secured === null ? "" : r.secured ? "yes" : "no", interest: r.interest === null ? "" : r.interest ? "yes" : "no", collect_within: r.collect_within ?? "", kind: r.kind ?? "",
  rate: r.rate ?? "", accrued_interest: (r.accrued_interest ?? "").replace(".", ",") });
const fromDraft = (d: Draft) => ({ name: d.name, amount: d.amount, grouped: d.grouped, related: d.related,
  secured: d.secured === "" ? null : d.secured === "yes", interest: d.interest === "" ? null : d.interest === "yes", collect_within: d.collect_within || null, kind: d.kind || null,
  rate: d.rate || null, accrued_interest: d.accrued_interest || null });

/** Sổ phải thu bên liên quan: the owner copies each year's notes; the app sets the years side by side and says what a later year stops naming. */
export function RelatedReceivables({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [year, setYear] = useState("");
  const [source, setSource] = useState("");
  const [rows, setRows] = useState<Draft[]>([{ ...EMPTY }]);
  const [busy, setBusy] = useState(false);
  const [aiUrl, setAiUrl] = useState("");
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => { api<View>(`related-receivables/${symbol}`).then(setView, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [symbol]);
  if (!view) return error ? <section className="surface" aria-label="Phải thu bên liên quan"><h2>Phải thu bên liên quan</h2><p className="muted">{error}</p></section> : null;

  function edit(y: Year) { setYear(y.year); setSource(y.source); setRows(y.rows.map(toDraft)); setError(null); }
  function setRow(i: number, patch: Partial<Draft>) { setRows(rows.map((r, k) => (k === i ? { ...r, ...patch } : r))); }
  async function send(path: string, body: object) {
    setBusy(true); setError(null);
    try {
      setView(await api<View>(path, { method: path.endsWith("/delete") ? "POST" : "PUT", body: { ...body, expected_version: view!.version, request_id: requestId() } }));
      return true;
    } catch (e) { setError(e instanceof ApiError ? e.failure.message : "Không lưu được."); return false; } finally { setBusy(false); }
  }
  async function propose() {
    if (!/^20\d{2}$/.test(year.trim())) { setError("Nhập năm trước, dạng 2020."); return; }
    setBusy(true); setError(null); setNote(null);
    try {
      const p = await api<Proposal>(`ai-docs/${symbol}/related-receivables`, { method: "POST", body: { url: aiUrl, year: year.trim() } });
      if (p.rows.length) {
        setRows(p.rows.map(toDraft));
        setSource((s) => s || `BCTC năm ${year.trim()}, thuyết minh bên liên quan (AI đề xuất, đã đối chiếu): ${p.url}`);
      }
      setNote(proposalNote(p));
    } catch (e) { setError(e instanceof ApiError ? e.failure.message : "AI chưa đề xuất được."); } finally { setBusy(false); }
  }
  async function save() {
    if (!/^20\d{2}$/.test(year.trim())) { setError("Năm theo dạng 2020."); return; }
    if (await send(`related-receivables/${symbol}/${year.trim()}`, { source, rows: rows.filter((r) => r.name.trim() || r.amount.trim()).map(fromDraft) })) {
      setYear(""); setSource(""); setRows([{ ...EMPTY }]);
    }
  }

  return (
    <section className="surface" aria-label="Phải thu bên liên quan">
      <h2>Phải thu bên liên quan</h2>
      <p className="caption">Chép từ thuyết minh phải thu, trả trước cho người bán (các nhà cung cấp chiếm từ 10% được nêu tên) và giao dịch với bên liên quan của từng năm (đơn vị tỷ đồng, kèm nguồn). Phần mềm đặt các năm cạnh nhau
        và báo khi một đối tượng có tên năm trước không còn được nêu năm sau, khi khoản hứa thu trong hạn vẫn còn từ một nửa, và khoản bên liên quan không bảo đảm,
        không lãi. Số do bạn nhập; lưu trên máy, không gửi đi đâu.</p>
      {view.findings.length > 0 && <ul className="quality-list" data-testid="rr-findings">{view.findings.map((f, i) => (
        <li key={i}><span className="pill warn">{f.kind === "vanished" ? "Không còn nêu tên" : f.kind === "not_collected" ? "Chưa thu" : f.kind === "interest_piling" ? "Lãi treo tăng" : "Không bảo đảm, không lãi"}</span> {findingText(f)}</li>))}
      </ul>}
      {view.years.map((y) => (
        <div key={y.year} className="rr-year">
          <h3>Năm {y.year} <span className="caption">— {y.source}</span></h3>
          <div className="tablewrap"><table className="fv-table" aria-label={`Phải thu bên liên quan năm ${y.year}`}>
            <thead><tr><th>Đối tượng</th><th>Loại</th><th className="num">Số dư</th><th>Bên liên quan</th><th>Bảo đảm</th><th>Có lãi</th><th>Lãi suất</th><th className="num">Lãi phải thu</th><th>Hạn thu</th></tr></thead>
            <tbody>{y.rows.map((r) => (
              <tr key={r.name}>
                <td data-label="Đối tượng">{r.name}{r.grouped && <span className="caption"> (dòng gộp)</span>}</td>
                <td data-label="Loại">{r.kind ? KIND[r.kind] : "—"}</td>
                <td className="num" data-label="Số dư">{ty(r.amount)}</td>
                <td data-label="Bên liên quan">{r.related ? "có" : "không"}</td>
                <td data-label="Bảo đảm">{tri(r.secured)}</td>
                <td data-label="Có lãi">{tri(r.interest)}</td>
                <td data-label="Lãi suất">{r.rate ?? "—"}</td>
                <td className="num" data-label="Lãi phải thu">{r.accrued_interest ? ty(r.accrued_interest) : "—"}</td>
                <td data-label="Hạn thu">{r.collect_within ?? "—"}</td>
              </tr>))}
            </tbody>
          </table></div>
          <p className="caption">Phải thu bên liên quan {ty(y.related_total)}, trong đó nêu tên {ty(y.named_related)}.
            {y.accrued_interest ? ` Lãi cho vay phải thu ${ty(y.accrued_interest)}.` : ""}{" "}
            <button type="button" className="btn text" disabled={busy} onClick={() => edit(y)}>Sửa năm {y.year}</button>{" "}
            <button type="button" className="btn text" disabled={busy} onClick={() => send(`related-receivables/${symbol}/${y.year}/delete`, {})}>Xóa năm {y.year}</button></p>
        </div>))}

      <h3>{view.years.some((y) => y.year === year.trim()) ? `Sửa năm ${year.trim()}` : "Thêm một năm"}</h3>
      <form className="formgrid" aria-label="Nhập phải thu bên liên quan" onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <label className="field">Năm<input aria-label="Năm báo cáo" inputMode="numeric" maxLength={4} value={year} onChange={(e) => setYear(e.target.value)} /></label>
        <label className="field">Nguồn<input aria-label="Nguồn thuyết minh" maxLength={300} value={source} placeholder="BCTC hợp nhất 2020, thuyết minh 38"
          onChange={(e) => setSource(e.target.value)} /></label>
        {rows.map((r, i) => (
          <fieldset key={i} className="rr-row">
            <legend>Dòng {i + 1}</legend>
            <label className="field">Đối tượng<input aria-label={`Đối tượng dòng ${i + 1}`} maxLength={120} value={r.name} onChange={(e) => setRow(i, { name: e.target.value })} /></label>
            <label className="field">Số dư (tỷ)<input aria-label={`Số dư dòng ${i + 1}`} inputMode="decimal" value={r.amount} onChange={(e) => setRow(i, { amount: e.target.value })} /></label>
            <label className="check"><input type="checkbox" checked={r.related} onChange={(e) => setRow(i, { related: e.target.checked })} /> Bên liên quan</label>
            <label className="check"><input type="checkbox" checked={r.grouped} onChange={(e) => setRow(i, { grouped: e.target.checked })} /> Dòng gộp (không nêu tên)</label>
            <label className="field">Bảo đảm<select aria-label={`Bảo đảm dòng ${i + 1}`} value={r.secured} onChange={(e) => setRow(i, { secured: e.target.value as Draft["secured"] })}>
              <option value="">Không rõ</option><option value="yes">Có</option><option value="no">Không</option></select></label>
            <label className="field">Có lãi<select aria-label={`Có lãi dòng ${i + 1}`} value={r.interest} onChange={(e) => setRow(i, { interest: e.target.value as Draft["interest"] })}>
              <option value="">Không rõ</option><option value="yes">Có</option><option value="no">Không</option></select></label>
            <label className="field">Loại<select aria-label={`Loại dòng ${i + 1}`} value={r.kind} onChange={(e) => setRow(i, { kind: e.target.value as Draft["kind"] })}>
              <option value="">Không rõ</option>{(Object.keys(KIND) as RrKind[]).map((k) => <option key={k} value={k}>{KIND[k]}</option>)}</select></label>
            <label className="field">Lãi suất<input aria-label={`Lãi suất dòng ${i + 1}`} maxLength={60} placeholder="8%–8,6%/năm" value={r.rate}
              onChange={(e) => setRow(i, { rate: e.target.value })} /></label>
            <label className="field">Lãi phải thu (tỷ)<input aria-label={`Lãi phải thu dòng ${i + 1}`} inputMode="decimal" value={r.accrued_interest}
              onChange={(e) => setRow(i, { accrued_interest: e.target.value })} /></label>
            <label className="field">Hạn thu<input aria-label={`Hạn thu dòng ${i + 1}`} maxLength={60} placeholder="6–12 tháng" value={r.collect_within}
              onChange={(e) => setRow(i, { collect_within: e.target.value })} /></label>
            {rows.length > 1 && <button type="button" className="btn text" onClick={() => setRows(rows.filter((_, k) => k !== i))}>Bỏ dòng {i + 1}</button>}
          </fieldset>))}
        <div className="actions rr-ai">
          <label className="field">Link BCTC để AI đề xuất<input aria-label="Link BCTC cho AI" type="url" maxLength={500} placeholder="https://…/bctc-2020.pdf"
            value={aiUrl} onChange={(e) => setAiUrl(e.target.value)} /></label>
          <button type="button" className="btn" disabled={busy || !aiUrl.trim()} onClick={() => void propose()}>AI đề xuất từ BCTC</button>
        </div>
        {note && <p className="notice" data-testid="rr-ai-note">{note}</p>}
        <div className="actions">
          <button type="button" className="btn" onClick={() => setRows([...rows, { ...EMPTY }])}>Thêm dòng</button>
          <button type="submit" className="btn primary" disabled={busy}>Lưu năm</button>
        </div>
        {error && <p className="errors" role="alert">{error}</p>}
      </form>
    </section>
  );
}
