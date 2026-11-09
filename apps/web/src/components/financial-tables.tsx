"use client";
import { useEffect, useState } from "react";
import { ChartColumn } from "lucide-react";
import { ApiError, api } from "../lib/api";
import { type Forecast, ForecastForm } from "./quarter-forecast";
import { Spark, StatementChart, seriesName, toggleRow } from "./statement-chart";

type Row = { key: string | null; label: string; kind: "group" | "money" | "pct" | "x" | "vnd"; indent: number; values: (string | null)[] };
type Part = { periods: string[]; rows: Row[] };
type Check = { period: string; check: string; label: string; a: string | null; b: string | null };
type Conflict = { period: string; line: string; values: string[] };
type Summary = { period: string; close_date: string | null; market_cap: string | null; npat_ttm: string | null; ebitda_ttm: string | null;
  ev: string | null; pe: string | null; pb: string | null; ev_ebitda: string | null; roe: string | null; roic?: string | null; quarters: string[] };
type Tables = { symbol: string; kind?: "bank" | "securities" | "insurance" | null; reason: string | null; source?: string; fetched_at?: string; quarters: Part; years: Part; summary: Summary | null;
  checks: Check[]; conflicts: Conflict[];
  valuation_check?: { shares_from_vndirect?: boolean; date: string | null; ours_date: string | null; flagged: number; rows: { key: string; label: string; note?: string | null; ours: string | null; theirs: string | null; diff: string | null; off: boolean }[] } | null };

type Kind = "bank" | "securities" | "insurance";
type Ratios = { kind: Kind; quarters: { date: string; label: string }[];
  metrics: { code: string; label: string; format: "pct0" | "pct1" | "pct2" | "times"; values: (string | null)[] }[];
  notes?: string[]; notes_fetched_at?: string | null };  // a bank's group-2 share and CASA: quarters left blank or entered differently

const SIGNED = new Set(["revenue_yoy", "gross_profit_yoy", "npat_parent_yoy", "ebitda_yoy", "fcff_yield"]);
// VNDirect's ratios read to two places (NPL 1,66%, not 1,7%), as their own table showed them.
const TWO = new Set(["BAD_LOANS_RATIO_AQ", "GROUP2_RATIO", "CAR", "OVERDUE_LOANS_RATIO_AQ", "NET_INTEREST_MARGIN_TR_AVG5Q", "ROAA_TR_AVG4Q", "LOANS_TO_EQUITY_AQ"]);
const TITLE: Record<Kind, string> = { bank: "ngân hàng", securities: "công ty chứng khoán", insurance: "bảo hiểm" };
const COUNTS = [8, 12, 20, 0] as const;

export function cell(v: string | null, kind: Row["kind"], key: string | null): string {
  if (v === null) return "—";
  const n = Number(v);
  if (kind === "money") return (Math.round(n / 1e9) || 0).toLocaleString("vi-VN");  // || 0: a small loss rounds to 0, not -0
  if (kind === "vnd") return `${Math.round(n).toLocaleString("vi-VN")} đ`;
  const places = key && TWO.has(key) ? 2 : 1;
  if (kind === "x") return `${n.toLocaleString("vi-VN", { minimumFractionDigits: places, maximumFractionDigits: places })}x`;
  const pct = (n * 100).toLocaleString("vi-VN", { minimumFractionDigits: places, maximumFractionDigits: places });
  return `${key && SIGNED.has(key) && n > 0 ? "+" : ""}${pct}%`;
}

export function periodLabel(p: string): string {
  return p.includes("-Q") ? `Q${p.slice(-1)}/${p.slice(2, 4)}` : p;
}

/** Indexes of the last n periods (all of them when n is 0). */
export function lastN<T>(periods: T[], n: number): number[] {
  const start = n === 0 ? 0 : Math.max(0, periods.length - n);
  return periods.map((_, i) => i).slice(start);
}

/** One line per period, newest first: every check that failed there with its two figures in tỷ đồng. */
export function checkLines(checks: Check[]): string[] {
  const by = new Map<string, Check[]>();
  for (const c of checks) by.set(c.period, [...(by.get(c.period) ?? []), c]);
  return [...by.keys()].sort().reverse().map((p) => `${periodLabel(p)} · ${by.get(p)!
    .map((c) => `${c.label} (${c.a === null ? "—" : cell(c.a, "money", null)} so với ${c.b === null ? "—" : cell(c.b, "money", null)} tỷ)`).join("; ")}`);
}

const tone = (v: string | null, key: string | null) => (v !== null && key && SIGNED.has(key) ? (Number(v) > 0 ? "positive" : Number(v) < 0 ? "negative" : "") : "");
const ty = (v: string | null) => (v === null ? "—" : `${cell(v, "money", null)} tỷ`);

type Extra = { label: string; values: Record<string, string | null> } | null;  // the owner's forecast column, shown after the last quarter

function Table({ part, cols, caption, extra = null, picked, onPick }: { part: Part; cols: number[]; caption: string; extra?: Extra; picked: string[];
  onPick: (key: string) => void }) {
  return (
    <div className="pb-scroll">
      <table className="pb-table ft-table">
        <caption className="caption">{caption}</caption>
        <thead><tr><th>Tỷ đồng</th>{cols.map((i) => <th key={part.periods[i]} className="num">{periodLabel(part.periods[i])}</th>)}
          {extra && <th className="num ft-forecast">{extra.label}</th>}<th>Xu hướng</th></tr></thead>
        <tbody>{part.rows.map((r, k) => r.kind === "group"
          ? <tr key={`g${k}`} className="ft-group"><th colSpan={cols.length + 2 + (extra ? 1 : 0)}>{r.label}</th></tr>
          : <tr key={r.key ?? k} className={r.key && picked.includes(r.key) ? "ft-picked" : undefined}><td className={r.indent ? "ft-indent" : undefined}>
            {r.key ? <>
              {/* The label is a mouse shortcut; the icon button is the keyboard and screen-reader way to the same toggle. */}
              <span className="ft-label" onClick={() => onPick(r.key!)}>{r.label}</span>
              <button type="button" className="ft-pick" aria-pressed={picked.includes(r.key)} aria-label={`Vẽ biểu đồ: ${seriesName(part.rows, r.key)}`}
                title="Vẽ dòng này trên biểu đồ" onClick={() => onPick(r.key!)}><ChartColumn size={13} aria-hidden="true" /></button>
            </> : r.label}</td>
            {cols.map((i) => <td key={part.periods[i]} className={`num ${tone(r.values[i], r.key)}`}>{cell(r.values[i], r.kind, r.key)}</td>)}
            {extra && <td className={`num ft-forecast ${tone(extra.values[r.key ?? ""] ?? null, r.key)}`}>{cell(extra.values[r.key ?? ""] ?? null, r.kind, r.key)}</td>}
            <td className="ft-spark"><Spark row={r} cols={cols} /></td></tr>)}</tbody>
      </table>
    </div>
  );
}

const FINANCIAL = new Set(["bank", "securities", "insurance"]);

/** A bank's, securities firm's or insurer's quarters with its sector ratios (VNDirect) as the first group, over the quarters of both;
 * a quarter one side lacks stays blank. */
export function withRatios(part: Part, ratios: Ratios): Part {
  const own = ratios.quarters.map((q) => `${q.date.slice(0, 4)}-Q${Math.floor((Number(q.date.slice(5, 7)) - 1) / 3) + 1}`);
  const periods = [...new Set([...part.periods, ...own])].sort();
  const at = (from: string[], values: (string | null)[]) => periods.map((p) => { const i = from.indexOf(p); return i < 0 ? null : values[i] ?? null; });
  const ratioRows: Row[] = [{ key: null, label: `Chỉ số ${TITLE[ratios.kind]}`, kind: "group", indent: 0, values: [] },
    ...ratios.metrics.map((m) => ({ key: m.code, label: m.label, kind: m.format === "times" ? "x" as const : "pct" as const, indent: 0, values: at(own, m.values) }))];
  return { periods, rows: [...ratioRows, ...part.rows.map((r) => (r.kind === "group" ? r : { ...r, values: at(part.periods, r.values) }))] };
}

const PICKED: Record<string, string[]> = { insurance: ["ins_result", "fin_profit"], bank: ["pb", "roe"], securities: ["pb", "roe"] };

/** Bảng số tài chính: a non-financial company's statements, or a bank's, securities firm's or insurer's sector ratios with its scale
 * and valuation block, with the same chart, period buttons and table. */
export function FinancialTables({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Tables | null>(null);
  const [ratios, setRatios] = useState<Ratios | null>(null);
  const [ratioError, setRatioError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"quarters" | "years">("quarters");
  const [count, setCount] = useState<(typeof COUNTS)[number]>(8);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [picked, setPicked] = useState<string[]>(["revenue", "gross_margin"]);
  useEffect(() => {
    const sym = encodeURIComponent(symbol);
    api<Tables>(`fairvalue/statements/${sym}`).then((d) => {
      if (d.kind && FINANCIAL.has(d.kind)) {
        setPicked(PICKED[d.kind]);
        api<Ratios>(`fairvalue/ratios/${sym}`).then(setRatios, (e) => setRatioError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
      } else {
        api<Forecast>(`quarter-forecast/${sym}`).then(setForecast, () => setForecast(null));
      }
      setData(d);
    }, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted fx-loading" role="status">Đang tải bảng số…</p>;
  const financial = FINANCIAL.has(data.kind ?? "");
  if (data.reason && !(financial && ratios)) return <p className="muted">Chưa có bảng số tài chính: {data.reason}.</p>;
  const part = view === "quarters" && ratios ? withRatios(data.quarters, ratios) : data[view];
  const cols = view === "quarters" ? lastN(part.periods, count) : lastN(part.periods, 0);
  const s = data.summary;
  const extra = view === "quarters" && forecast?.quarter && Object.keys(forecast.values).length ? { label: `${periodLabel(forecast.quarter)}F`, values: forecast.values } : null;
  return (
    <div className="ft">
      {s && <div className="pb-cards" aria-label="Bốn quý gần nhất">
        <div><span className="caption">LNST công ty mẹ 4 quý ({s.quarters.map(periodLabel).join(", ")})</span><strong>{ty(s.npat_ttm)}</strong></div>
        <div><span className="caption">EBITDA 4 quý</span><strong>{ty(s.ebitda_ttm)}</strong></div>
        <div><span className="caption">ROE 4 quý</span><strong>{cell(s.roe, "pct", null)}</strong></div>
        <div title="LN HĐKD lõi 4 quý × (1 − thuế thực tế) ÷ vốn đầu tư bình quân (vốn chủ gồm cổ đông thiểu số + vay − tiền và đầu tư ngắn hạn), đầu và cuối 4 quý">
          <span className="caption">ROIC vận hành 4 quý</span><strong>{cell(s.roic ?? null, "pct", null)}</strong></div>
        <div><span className="caption">P/E · P/B · EV/EBITDA {s.close_date ? `(giá ${s.close_date.split("-").reverse().join("/")})` : ""}</span>
          <strong>{cell(s.pe, "x", null)} · {cell(s.pb, "x", null)} · {cell(s.ev_ebitda, "x", null)}</strong></div>
      </div>}
      <div className="pb-head">
        <span className="pb-toggle" role="radiogroup" aria-label="Kỳ">{(["quarters", "years"] as const).map((v) =>
          <button key={v} type="button" role="radio" aria-checked={view === v} className={`btn ${view === v ? "primary" : ""}`} onClick={() => setView(v)}>
            {v === "quarters" ? "Quý" : "Năm"}</button>)}</span>
        {view === "quarters" && <span className="pb-toggle" role="group" aria-label="Số quý">{COUNTS.map((n) =>
          <button key={n} type="button" className={`btn ${count === n ? "primary" : ""}`} aria-pressed={count === n} onClick={() => setCount(n)}>
            {n === 0 ? "Tất cả" : `${n} quý`}</button>)}</span>}
      </div>
      {financial && view === "years" && <p className="caption">Chỉ số {TITLE[data.kind as Kind]} chỉ có theo quý; chế độ Năm chỉ có Quy mô và định giá.</p>}
      {ratioError && <p className="errors" role="alert">Chưa có chỉ số {TITLE[data.kind as Kind]}: {ratioError}</p>}
      {part.periods.length === 0 ? <p className="muted">Chưa có kỳ nào.</p>
        : <>
          <StatementChart rows={part.rows} periods={part.periods} cols={cols} keys={picked} forecast={extra} checks={data.checks}
            onRemove={(key) => setPicked((p) => p.filter((k) => k !== key))} />
          <Table part={part} cols={cols} caption={`${view === "quarters" ? `${cols.length} quý, cũ bên trái` : `${cols.length} năm`} · bấm tên dòng để vẽ (tối đa 2 dòng)`}
            extra={extra} picked={picked} onPick={(key) => setPicked((p) => toggleRow(p, key))} />
        </>}
      {!financial && view === "quarters" && forecast && <ForecastForm key={`${forecast.quarter}-${forecast.version}`} symbol={symbol} data={forecast} onSaved={setForecast} />}
      {data.valuation_check && <details className="mc-table" aria-label="Đối chiếu định giá">
        <summary>Đối chiếu định giá với VNDirect: {data.valuation_check.flagged ? `${data.valuation_check.flagged} chỉ tiêu lệch hơn 10%` : "không lệch quá 10%"}</summary>
        <div className="tablewrap"><table aria-label="Đối chiếu định giá với VNDirect">
          <thead><tr><th>Chỉ tiêu</th><th className="num">Phần mềm</th><th className="num">VNDirect</th><th className="num">Lệch</th></tr></thead>
          <tbody>{data.valuation_check.rows.map((r) => <tr key={r.key}><td>{r.label}</td>
            <td className="num">{r.ours === null ? "—" : r.key === "market_cap" ? ty(r.ours) : cell(r.ours, "x", null)}</td>
            <td className="num">{r.theirs === null ? "—" : r.key === "market_cap" ? ty(r.theirs) : cell(r.theirs, "x", null)}</td>
            <td className={`num ${r.off ? "negative" : ""}`}>{r.diff === null ? "—" : `${(Number(r.diff) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`}</td></tr>)}</tbody>
        </table></div>
        {data.valuation_check.rows.filter((r) => r.note).map((r) => <p key={r.key} className="notice">{r.label}: {r.note}</p>)}
        <p className="caption">Phần mềm tính theo giá đóng cửa mới nhất đã lưu{data.valuation_check.ours_date ? ` (${data.valuation_check.ours_date.split("-").reverse().join("/")})` : ""}, VNDirect theo số của họ{data.valuation_check.date ? ` (${data.valuation_check.date.split("-").reverse().join("/")})` : ""}. Hai bên có thể khác cách tính lợi nhuận và số cổ phiếu; lệch hơn 10% thì nên xem lại, phần mềm không tự chỉnh số.{data.valuation_check.shares_from_vndirect && " Mã này: vốn hoá tính theo số cổ phiếu cuối quý lệch hơn 10%, nên phần mềm dùng số cổ phiếu hiện tại của VNDirect, vì vậy hai bên gần như trùng và không còn là phép kiểm tra độc lập."}</p>
      </details>}
      {(data.checks.length > 0 || data.conflicts.length > 0) && <details className="mc-table">
        <summary>Kiểm tra chéo: {data.checks.length} chỗ lệch hơn 0,5% ở {new Set(data.checks.map((c) => c.period)).size} kỳ{data.conflicts.length ? `, ${data.conflicts.length} dòng nguồn ghi hai số` : ""}</summary>
        <ul className="ft-checks">
          {checkLines(data.checks).map((line) => <li key={line}>{line}</li>)}
          {data.conflicts.map((c) => <li key={`${c.period}-${c.line}`}>{periodLabel(c.period)} · dòng {c.line}: nguồn ghi {c.values.map(ty).join(" và ")}, không lấy số nào</li>)}
        </ul>
      </details>}
      {ratios?.notes && ratios.notes.length > 0 && <details className="mc-table">
        <summary>Đối chiếu nợ nhóm 2, CASA và CAR: {ratios.notes.length} ghi chú</summary>
        <ul className="ft-checks">{ratios.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      </details>}
      {financial ? <p className="caption wrap">
        Chỉ số {TITLE[data.kind as Kind]}: tỷ lệ VNDirect tính sẵn (dữ liệu công khai, từ Q4/2017; ROAA, ROAE từ Q3/2023), chỉ có theo quý; NIM, ROAA, ROAE,
        biên lợi nhuận trên 4–5 quý gần nhất, các tỷ lệ khác tại cuối quý; ô — là quý nguồn chưa có số.{data.kind === "bank" ? ` Tỷ lệ nợ nhóm 2 = nợ nhóm 2 / nợ nhóm 1–5 và CASA = (tiền gửi không kỳ hạn + ký quỹ) / tiền gửi của khách hàng: từ thuyết minh báo cáo tài chính trên API công khai của Vietcap (từ Q1/2018${ratios?.notes_fetched_at ? `, đọc ${new Date(ratios.notes_fetched_at).toLocaleDateString("vi-VN")}` : ""}), chỉ ở quý mà các nhóm nợ và các loại tiền gửi cộng ra đúng tổng; quý đã nhập ở Số liệu ngân hàng (nhập tay) dùng số nhập tay. CAR (cuối năm): tỷ lệ an toàn vốn cuối năm của Vietcap, ở cột Q4 (không nguồn miễn phí nào có CAR theo quý); năm Vietcap chưa có thì dùng số của VNDirect (trừ mức 8% giữ chỗ); hai nguồn lệch quá 0,1 điểm hoặc Vietcap trùng đúng năm trước thì ghi ở mục đối chiếu. Thiếu thì để trống, không nội suy.` : ""} Quy mô và định giá: báo cáo tài chính trên API công
        khai của VNDirect{data.fetched_at ? `, đọc ${new Date(data.fetched_at).toLocaleDateString("vi-VN")}` : ""}. Vốn hoá = giá đóng
        cửa thực (chưa điều chỉnh) phiên cuối kỳ × số cổ phiếu cuối kỳ (vốn góp ÷ 10.000 đ); giá thực có từ 2013. Vốn chủ công ty mẹ = vốn chủ sở hữu − lợi
        ích cổ đông không kiểm soát; giá trị sổ sách / cổ phiếu = vốn chủ công ty mẹ ÷ số cổ phiếu. Quý: P/E, ROE và các bội số theo lợi nhuận, thu nhập tính
        trên 4 quý tới quý đó (thiếu một quý thì để trống); năm: số cả năm. ROE = LNST công ty mẹ ÷ vốn chủ công ty mẹ bình quân kỳ đó và cùng kỳ năm
        trước, nên có thể lệch ROAE của VNDirect ở nhóm chỉ số. {data.kind === "bank" ? "LN trước dự phòng = lợi nhuận thuần từ hoạt động kinh doanh trước chi phí dự phòng rủi ro tín dụng."
          : data.kind === "securities" ? "Vay = vay và nợ ngắn hạn + dài hạn, trên vốn chủ sở hữu (cả phần không kiểm soát)."
          : "Danh mục đầu tư = tiền + đầu tư tài chính ngắn hạn + dài hạn, trên vốn chủ sở hữu (cả phần không kiểm soát). Kết quả kinh doanh bảo hiểm = lợi nhuận thuần từ hoạt động kinh doanh bảo hiểm; với bảo hiểm nhân thọ thường âm vì khoản tăng dự phòng toán học ghi vào chi phí và được bù bằng lãi đầu tư, không có nghĩa là lỗ. Chỉ hiện ở kỳ mà kết quả bảo hiểm, lợi nhuận hoạt động tài chính và các khoản khác cộng ra đúng LNTT (từ giữa 2014; mẫu báo cáo cũ không cộng ra được, để trống và ghi ở Kiểm tra chéo). Không tính P/EV: giá trị nội tại không có trong báo cáo tài chính. Tỷ lệ kết hợp là số của VNDirect ở nhóm chỉ số."} Không
        tính nợ ròng, EV, EBITDA, FCFF: với ngân hàng, công ty chứng khoán và bảo hiểm, đi vay hay giữ tiền của khách là hoạt động kinh doanh. Thiếu một thành phần thì để trống, không ước lượng.
      </p> : <p className="caption wrap">
        Nguồn: báo cáo tài chính trên API công khai của VNDirect{data.fetched_at ? `, đọc ${new Date(data.fetched_at).toLocaleDateString("vi-VN")}` : ""}; số từng quý (không lũy kế),
        chi phí ghi số âm. LN HĐKD lõi = lãi gộp − chi phí bán hàng − quản lý. EBIT = LNTT + lãi vay; EBITDA = EBIT + khấu hao. FCFF = lưu chuyển tiền
        HĐKD + lãi vay × (1 − thuế ÷ LNTT) + capex; không tính khi LNTT ≤ 0. Vốn hoá năm = giá đóng cửa thực (chưa điều chỉnh) phiên cuối năm × số cổ
        phiếu cuối năm (vốn góp ÷ 10.000 đ); giá thực có từ 2013, năm trước đó để trống; vốn hoá quý tương tự theo phiên cuối quý và số cổ
        phiếu cuối quý, còn P/E, EV/EBITDA, EV/doanh thu, lợi suất FCFF và ROE của quý tính trên 4 quý tới quý đó (thiếu một quý thì để trống); vốn hoá ở thẻ 4 quý theo giá gần nhất × số cổ phiếu hiện tại; nợ ròng = nợ vay
        ngắn + dài hạn − tiền − đầu tư tài chính ngắn hạn; EV = vốn hoá + nợ ròng + lợi ích cổ đông không kiểm soát; P/B trên vốn chủ của công ty mẹ;
        ROE = LNST công ty mẹ ÷ vốn chủ bình quân đầu và cuối kỳ. Thiếu một thành phần thì để trống, không ước lượng. Kiểm tra chéo: lãi gộp với doanh thu
        − giá vốn, tổng 4 quý với cả năm, LNST với nguồn Vnstock; dòng tiền quý những năm cũ thường lệch số cả năm đã kiểm toán.
      </p>}
    </div>
  );
}
