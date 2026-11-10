"use client";
import { useEffect, useState } from "react";
import { FileSearch, Pencil, Save, Trash2 } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio } from "../lib/format";

const FIELDS = ["group1", "group2", "group3", "group4", "group5", "demand_deposits", "margin_deposits", "customer_deposits", "car", "reserve", "accrued_interest",
  "real_estate_loans", "discounted_documents"] as const;
type Field = (typeof FIELDS)[number];
// A quarter's figures can come from two files (statements, and the separate CAR report): each field keeps its file and page.
type Source = { kind: "manual" } | { kind: "pdf"; url: string | null; pages: Partial<Record<Field, number>>; urls?: Partial<Record<Field, string>> };
type Quarter = { quarter: string; values: Record<Field, string | null>; source: Source;
  derived: { npl: string | null; group2_ratio: string | null; casa: string | null; car: string | null; llr?: string | null; real_estate_share?: string | null }; trend?: Trend };
type Trend = { llr: string | null; llr_prev: string | null; llr_year_ago: string | null; llr_start: string | null; group2_growth_qoq: string | null; loans_growth_qoq: string | null;
  loans_growth_ytd: string | null; accrued_growth_qoq: string | null; documents_growth_qoq: string | null; real_estate_growth_ytd: string | null; flags: string[] };
type View = { symbol: string; version: number; quarters: Quarter[]; labels: Record<Field, string> };
// `ocr`: read from a scanned page by OCR on this machine, already checked against the printed total where there is one.
type Read = { url: string; fields: Partial<Record<Field, { value: string; page: number; ocr?: boolean }>>; missing: Field[]; warnings: string[];
  ocr_pages?: number[] };

const pct = (v: string | null | undefined) => (v ? formatRatio(v, 2) : "—");
const pct1 = (v: string | null | undefined) => (v ? formatRatio(v, 1) : "—");
/** The warning signs of the latest quarter, each with the figures behind it. */
export function flagText(code: string, t: Trend): string {
  switch (code) {
    case "llr_falling": return `Bao phủ nợ xấu giảm còn ${pct1(t.llr)} (quý trước ${pct1(t.llr_prev)}, đầu năm ${pct1(t.llr_start)}, cùng kỳ ${pct1(t.llr_year_ago)}).`;
    case "group2_jump": return `Nợ nhóm 2 tăng ${pct1(t.group2_growth_qoq)} so với quý trước: ứng viên chuyển thành nợ xấu.`;
    case "reserve_lagging": return "Nợ xấu tăng nhưng số dư dự phòng giảm so với quý trước: dự phòng chưa theo kịp.";
    case "write_off": return "Nợ nhóm 5 và dự phòng cùng giảm: có thể đã dùng dự phòng để xử lý (xóa) nợ.";
    case "accrued_jump": return `Lãi và phí phải thu tăng ${pct1(t.accrued_growth_qoq)} so với quý trước: phần lợi nhuận chưa thu bằng tiền tăng.`;
    case "real_estate_fast": return `Dư nợ bất động sản tăng ${pct1(t.real_estate_growth_ytd)} từ đầu năm, nhanh hơn tổng dư nợ (${pct1(t.loans_growth_ytd)}).`;
    case "documents_jump": return `Chiết khấu bộ chứng từ, phải thu ngoài cho vay tăng ${pct1(t.documents_growth_qoq)} so với quý trước: cấp vốn nằm ngoài chỉ tiêu tín dụng.`;
    default: return code;
  }
}
/** The quarter to type next: the last one that has ended, or the latest earlier one not saved yet (up to two years back). */
export function quarterToEnter(today: Date, saved: string[]): string {
  let year = today.getFullYear(), q = Math.floor(today.getMonth() / 3);  // the quarter before the current one (0 = Q4 of last year)
  if (q === 0) { year -= 1; q = 4; }
  const first = `${year}-Q${q}`;
  for (let i = 0; i < 8; i++) {
    const label = `${year}-Q${q}`;
    if (!saved.includes(label)) return label;
    if (--q === 0) { year -= 1; q = 4; }
  }
  return first;
}

const blank = () => Object.fromEntries(FIELDS.map((f) => [f, ""])) as Record<Field, string>;
const toInput = (v: string | null) => (v ?? "").replace(".", ",");
/** Typed number to a plain decimal: "537.304,578" (Vietnamese), "537.304" (thousands) and "537304.578" (decimal point) all read right. */
export function fromInput(raw: string): string {
  const v = raw.trim().replace(/\s/g, "");
  if (v.includes(",")) return v.replace(/\./g, "").replace(",", ".");
  return /^\d{1,3}(\.\d{3})+$/.test(v) ? v.replace(/\./g, "") : v;
}

const sourceFiles = (s: Extract<Source, { kind: "pdf" }>) => [...new Set([...Object.values(s.urls ?? {}), ...(s.url ? [s.url] : [])])];
const fileName = (u: string | null | undefined) => (u ? decodeURIComponent(u.split("/").pop() ?? "PDF") : "PDF");
/** Where a proposed value came from, and a reminder when OCR read it from an image: a misread digit is possible. */
export const pageNote = (page: number, file: string, ocr: boolean) =>
  `trang ${page} trong ${file}${ocr ? " · đọc từ ảnh (OCR), so lại từng chữ số" : ""}`;

/** Owner-entered bank figures per quarter (loans by group, deposits, CAR), with a PDF reader that only proposes values. */
export function BankFigures({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [hidden, setHidden] = useState(false);
  const [quarter, setQuarter] = useState("");
  const [values, setValues] = useState(blank);
  const [source, setSource] = useState<Source>({ kind: "manual" });
  const [url, setUrl] = useState("");
  const [read, setRead] = useState<Read | null>(null);
  const [fromImage, setFromImage] = useState<Set<Field>>(new Set());  // fields filled by OCR and not yet saved
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<View>(`bank-figures/${encodeURIComponent(symbol)}`).then((v) => { setView(v); setQuarter(quarterToEnter(new Date(), v.quarters.map((q) => q.quarter))); }, (e) => {
      if (e instanceof ApiError && e.failure.code === "not_a_watched_bank") setHidden(true); else setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
    });
  }, [symbol]);
  if (hidden) return null;

  function edit(q: Quarter) {
    setQuarter(q.quarter); setValues(Object.fromEntries(FIELDS.map((f) => [f, toInput(q.values[f])])) as Record<Field, string>);
    setSource(q.source); setRead(null); setFromImage(new Set()); setMessage(null);
  }
  async function readPdf() {
    if (!url.trim()) { setMessage("Dán đường dẫn https của file PDF báo cáo."); return; }
    setBusy(true);
    try {
      const r = await api<Read>(`bank-figures/${encodeURIComponent(symbol)}/read-pdf`, { method: "POST", body: { url: url.trim(), request_id: requestId() } });
      setRead(r);
      setFromImage((old) => {
        const next = new Set([...old].filter((f) => !(f in r.fields)));
        for (const [f, x] of Object.entries(r.fields)) if (x!.ocr) next.add(f as Field);
        return next;
      });
      setValues((old) => ({ ...old, ...Object.fromEntries(Object.entries(r.fields).map(([f, x]) => [f, toInput(x!.value)])) }));
      setSource((old) => {
        const before = old.kind === "pdf" ? old : { pages: {}, urls: {} };
        const found = Object.entries(r.fields);
        return { kind: "pdf", url: r.url, pages: { ...before.pages, ...Object.fromEntries(found.map(([f, x]) => [f, x!.page])) },
          urls: { ...(before.urls ?? {}), ...Object.fromEntries(found.map(([f]) => [f, r.url])) } };
      });
      setUrl("");
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi đọc file."); } finally { setBusy(false); }
  }
  async function save() {
    if (!view) return;
    if (!/^\d{4}-Q[1-4]$/.test(quarter.trim())) { setMessage("Nhập quý theo dạng 2026-Q3."); return; }
    try {
      const next = await api<View>(`bank-figures/${encodeURIComponent(symbol)}/${quarter.trim()}`, { method: "PUT",
        body: { values: Object.fromEntries(FIELDS.map((f) => [f, values[f].trim() ? fromInput(values[f]) : null])), source,
          expected_version: view.version, request_id: requestId() } });
      setView(next);
      setQuarter(quarterToEnter(new Date(), next.quarters.map((q) => q.quarter))); setValues(blank()); setSource({ kind: "manual" }); setRead(null); setFromImage(new Set()); setUrl(""); setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  async function remove(q: string) {
    if (!view || !window.confirm(`Xóa số liệu ${q}?`)) return;
    try {
      setView(await api<View>(`bank-figures/${encodeURIComponent(symbol)}/${q}/delete`, { method: "POST",
        body: { expected_version: view.version, request_id: requestId() } }));
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi xóa."); }
  }
  const pages = source.kind === "pdf" ? source.pages : {};
  return (
    <section className="surface" aria-label="Số liệu ngân hàng">
      <h2>Số liệu ngân hàng (nhập tay)</h2>
      <p className="caption">Nợ nhóm 1–5, tiền gửi, CAR và các số về chất lượng tài sản không có ở nguồn miễn phí: nhập từ thuyết minh báo cáo tài chính quý (tỷ đồng), hoặc dán đường dẫn PDF
        công khai để phần mềm đọc và điền sẵn — kiểm tra lại rồi mới lưu. File scan dạng ảnh được nhận dạng chữ (OCR) ngay trên máy, mất khoảng 1–2 phút;
        số đọc từ ảnh được cộng thử với dòng tổng, ô nào không khớp thì để trống. CASA = (không kỳ hạn + ký quỹ) / tiền gửi khách hàng. Nợ nhóm 2 và CASA
        đã tự lấy từ thuyết minh trên Vietcap (Điểm sức khỏe dùng cho tiêu chí CASA tăng, nợ nhóm 2 giảm); quý nhập ở đây được dùng thay số Vietcap.</p>
      {view && view.quarters.length > 0 && <table className="fv-table" aria-label={`Số liệu ngân hàng ${symbol}`}>
        <thead><tr><th>Quý</th><th className="num">NPL</th><th className="num">Nợ nhóm 2</th><th className="num">CASA</th><th className="num">CAR</th><th className="num">Bao phủ nợ xấu</th><th>Nguồn</th><th /></tr></thead>
        <tbody>{view.quarters.map((q) => <tr key={q.quarter}>
          <td data-label="Quý">{q.quarter}</td><td data-label="NPL" className="num">{pct(q.derived.npl)}</td>
          <td data-label="Nợ nhóm 2" className="num">{pct(q.derived.group2_ratio)}</td><td data-label="CASA" className="num">{pct(q.derived.casa)}</td>
          <td data-label="CAR" className="num">{pct(q.derived.car)}</td>
          <td data-label="Bao phủ nợ xấu" className="num">{pct1(q.derived.llr)}</td>
          <td data-label="Nguồn">{q.source.kind === "pdf" ? sourceFiles(q.source).map((u, i) => <a key={u} href={u} target="_blank" rel="noreferrer">
            {i ? " · " : ""}PDF {i + 1}</a>) : "Nhập tay"}</td>
          <td className="actions"><button type="button" className="btn" aria-label={`Sửa ${q.quarter}`} onClick={() => edit(q)}><Pencil size={14} aria-hidden="true" />Sửa</button>
            <button type="button" className="btn" aria-label={`Xóa ${q.quarter}`} onClick={() => void remove(q.quarter)}><Trash2 size={14} aria-hidden="true" />Xóa</button></td>
        </tr>)}</tbody>
      </table>}
      {view && view.quarters.length === 0 && <div className="bf-quality" data-testid="bank-quality">
        <h3>Chất lượng tài sản</h3>
        <p className="caption">Chưa có quý nào. Nhập và lưu quý gần nhất ở dưới (ô Quý đã điền sẵn) để xem tỷ lệ bao phủ nợ xấu; lưu thêm quý liền trước để phần mềm so và chỉ ra
          dấu hiệu cần xem kỹ: bao phủ giảm, nợ nhóm 2 tăng vọt, dự phòng không theo kịp, lãi phải thu hay dư nợ bất động sản tăng nhanh.</p>
      </div>}
      {view && view.quarters[0]?.trend && <div className="bf-quality" data-testid="bank-quality">
        <h3>Chất lượng tài sản {view.quarters[0].quarter}</h3>
        {view.quarters[0].trend.flags.length === 0
          ? <p className="caption">Chưa thấy dấu hiệu cần xem kỹ theo các ngưỡng bên dưới{view.quarters.length < 2 ? " (cần ít nhất hai quý liền nhau để so)" : ""}.</p>
          : <ul className="bf-flags">{view.quarters[0].trend.flags.map((f) => <li key={f}>{flagText(f, view.quarters[0].trend!)}</li>)}</ul>}
        <p className="caption">So với quý trước, cùng kỳ năm trước và cuối năm trước. Ngưỡng do phần mềm đặt: bao phủ nợ xấu giảm từ 10 điểm %, nợ nhóm 2 tăng từ 30%, lãi phải thu tăng từ 20%,
          chứng từ tăng từ 30%, dư nợ bất động sản tăng từ 10% và nhanh gấp 1,5 lần tổng dư nợ. Là dấu hiệu để đọc kỹ thuyết minh, không phải kết luận hay khuyến nghị. Ô để trống thì không so.</p>
      </div>}
      <div className="fv-search">
        <label className="field">Đường dẫn PDF báo cáo (https)<input type="url" value={url} placeholder="https://…/bctc-quy-3-2026.pdf" disabled={!view}
          onChange={(e) => setUrl(e.target.value)} /></label>
        <button type="button" className="btn" disabled={!view || busy} onClick={() => void readPdf()}><FileSearch size={16} aria-hidden="true" />
          {busy ? "Đang đọc… (file scan mất 1–2 phút)" : "Đọc và điền sẵn"}</button>
      </div>
      {read && <div className="notice" role="status">Đã điền {Object.keys(read.fields).length}/{FIELDS.length} ô từ PDF — kiểm tra lại với file trước khi lưu.
        {read.missing.length > 0 && <> Chưa tìm thấy: {read.missing.map((f) => view?.labels[f] ?? f).join(", ")}.</>}
        {read.warnings.map((w) => <div key={w}>{w}</div>)}</div>}
      <form className="eb-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
        <label className="field">Quý<input value={quarter} placeholder="2026-Q3" maxLength={7} disabled={!view} onChange={(e) => setQuarter(e.target.value)} /></label>
        {FIELDS.map((f) => <label key={f} className="field">{view?.labels[f] ?? f}{f === "car" ? "" : " (tỷ đồng)"}{f === "real_estate_loans" || f === "discounted_documents" ? " · nhập tay" : ""}
          <input inputMode="decimal" value={values[f]} disabled={!view} onChange={(e) => setValues({ ...values, [f]: e.target.value })} />
          {pages[f] && <span className="caption">{pageNote(pages[f], fileName(source.kind === "pdf" ? source.urls?.[f] ?? source.url : null), fromImage.has(f))}</span>}</label>)}
        <button type="submit" className="btn primary" disabled={!view}><Save size={16} aria-hidden="true" />Lưu quý này</button>
      </form>
      {message && <p className="errors" role="alert">{message}</p>}
    </section>
  );
}
