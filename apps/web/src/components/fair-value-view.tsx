"use client";
import Link from "next/link";
import { Fragment, useEffect, useMemo, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";
import { MultipleCharts } from "./multiple-chart";
import { FScoreCell, QualityList, type Quality } from "./report-quality";

export type Method = { method: string; label: string; value: string | null; reason: string | null; inputs: Record<string, string | number> };
export type Row = { symbol: string; sector: string; price: string | null; fair: string | null; low: string | null; high: string | null; gap: string | null;
  verdict: "cheap" | "fair" | "expensive" | "insufficient"; reason: string | null; methods: Method[]; latest_year: string | null;
  latest_quarter: string | null; held: boolean; quality?: Quality; new_quarter?: string | null };
export type IndexRow = { symbol: string; name: string; as_of: string | null; close: string | null; fair: string | null; low: string | null; high: string | null;
  gap: string | null; verdict: Row["verdict"]; reason: string | null; methods: Method[] };
type Board = { as_of: string; rows: Row[]; indices?: IndexRow[]; settings: { required_return: string; long_term_growth: string; threshold: string } };

export const VERDICT: Record<Row["verdict"], { label: string; tone: string }> = {
  cheap: { label: "Rẻ", tone: "good" }, fair: { label: "Hợp lý", tone: "" }, expensive: { label: "Đắt", tone: "bad" },
  insufficient: { label: "Chưa đủ dữ liệu", tone: "warn" },
};
const INPUT: Record<string, string> = { eps: "EPS", bvps: "Giá trị sổ sách/cp", pe_median: "P/E trung vị", pb_median: "P/B trung vị", years: "Số năm",
  base: "Cơ sở", peer_median: "Trung vị cùng ngành", peers: "Số mã cùng ngành", roe: "ROE", justified_pb: "P/B hợp lý",
  dividend_avg3: "Cổ tức tiền bình quân 3 năm", paying_years: "Số năm trả cổ tức" };
const pct = (v: string) => formatRatio(v, 1);
const signedPct = (v: string) => `${v.startsWith("-") ? "" : "+"}${pct(v)}`;
const vnDate = (iso: string) => iso.split("-").reverse().join("/");

function inputText(k: string, v: string | number) {
  if (typeof v === "number") return String(v);
  if (k === "roe" || k === "justified_pb" || k.endsWith("median")) return k === "roe" ? pct(v) : v.replace(".", ",").slice(0, 6);
  return formatVnd(v);
}

/** Each valuation method with its inputs, then the share-count caveat. */
export function MethodList({ row }: { row: Row }) {
  return (
    <section aria-label={`Phương án định giá ${row.symbol}`}>
      {row.methods.length === 0 && <p className="muted">{row.reason}</p>}
      <ul>{row.methods.map((m) => (
        <li key={m.method}><strong>{m.label}</strong>: {m.value ? formatVnd(m.value) : <span className="muted">Không áp dụng — {m.reason}</span>}
          {m.value && <span className="caption"> ({Object.entries(m.inputs).map(([k, v]) => `${INPUT[k] ?? k} ${inputText(k, v)}`).join(" · ")})</span>}</li>))}
      </ul>
      <p className="caption">Số cổ phiếu ước tính từ lợi nhuận / EPS năm {row.latest_year ?? "—"} và các đợt phát hành sau đó; có thể lệch vài phần trăm.</p>
    </section>
  );
}

/** VNINDEX and VN30: today's P/E and P/B against their own five-year median, same verdict rule as the tickers. */
function IndexTable({ rows }: { rows: IndexRow[] }) {
  const multiple = (m: Method | undefined) => !m ? "—" : m.value
    ? <>{formatDecimal(String(m.inputs.now), 2)} <span className="caption">· trung vị 5 năm {formatDecimal(String(m.inputs.median), 2)}</span></>
    : <span className="muted">{m.reason}</span>;
  const [open, setOpen] = useState<string | null>(null);
  return (
    <>
      <h2>Chỉ số thị trường</h2>
      <table className="fv-table" aria-label="Định giá chỉ số">
        <thead><tr><th>Chỉ số</th><th className="num">Điểm</th><th className="num">Mức hợp lý</th><th className="num">Chênh lệch</th><th>Kết luận</th>
          <th>P/E</th><th>P/B</th><th>Số liệu</th><th /></tr></thead>
        <tbody>{rows.map((r) => (
          <Fragment key={r.symbol}>
          <tr>
            <td data-label="Chỉ số"><strong>{r.name}</strong></td>
            <td data-label="Điểm" className="num">{r.close ? formatDecimal(r.close, 2) : "—"}</td>
            <td data-label="Mức hợp lý" className="num">{r.fair ? <>{formatDecimal(r.fair, 2)}<div className="caption">{formatDecimal(r.low, 2)} – {formatDecimal(r.high, 2)}</div></> : "—"}</td>
            <td data-label="Chênh lệch" className="num">{r.gap ? signedPct(r.gap) : "—"}</td>
            <td data-label="Kết luận"><span className={`pill ${VERDICT[r.verdict].tone}`}>{VERDICT[r.verdict].label}</span>{r.reason && <div className="caption">{r.reason}</div>}</td>
            <td data-label="P/E">{multiple(r.methods.find((m) => m.method === "pe_history"))}</td>
            <td data-label="P/B">{multiple(r.methods.find((m) => m.method === "pb_history"))}</td>
            <td data-label="Số liệu">{r.as_of ? vnDate(r.as_of) : "—"}</td>
            <td><button className="btn" aria-expanded={open === r.symbol} onClick={() => setOpen(open === r.symbol ? null : r.symbol)}
              aria-label={`Chi tiết ${r.name}`}>Chi tiết</button></td>
          </tr>
          {open === r.symbol && <tr className="fv-detail"><td colSpan={9}><MultipleCharts symbol={r.symbol} /></td></tr>}
          </Fragment>))}
        </tbody>
      </table>
      <p className="caption">P/E, P/B chỉ số theo ngày từ VNDirect; mức hợp lý = điểm × trung vị 5 năm / hiện tại, trung vị của hai phương án.
        P/E tính trên lợi nhuận bốn quý gần nhất nên đổi khi doanh nghiệp công bố báo cáo quý.</p>
      <h2>Cổ phiếu theo dõi</h2>
    </>
  );
}

export function FairValueView() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  useEffect(() => { api<Board>("fairvalue").then(setBoard, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const rows = useMemo(() => (board?.rows ?? []).filter((r) => filter === "all" || (filter === "held" ? r.held : r.verdict === filter))
    .sort((a, b) => (a.gap === null ? 1 : b.gap === null ? -1 : Number(a.gap) - Number(b.gap))), [board, filter]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!board) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const s = board.settings;
  return (
    <section className="surface">
      <p className="notice">Định giá tham khảo từ báo cáo tài chính công bố (Vnstock, gói miễn phí), không phải khuyến nghị. Lợi suất yêu cầu {pct(s.required_return)},
        tăng trưởng dài hạn {pct(s.long_term_growth)}, ngưỡng Rẻ/Đắt ±{pct(s.threshold)} so với giá hợp lý (trung vị các phương án). Sửa trong Cài đặt.</p>
      {board.indices && board.indices.length > 0 && <IndexTable rows={board.indices} />}
      <div className="actions" role="radiogroup" aria-label="Lọc">
        {[["all", "Tất cả"], ["cheap", "Rẻ"], ["fair", "Hợp lý"], ["expensive", "Đắt"], ["insufficient", "Chưa đủ dữ liệu"], ["held", "Đang nắm"]].map(([id, label]) => (
          <label key={id} className="choice"><input type="radio" name="fv-filter" checked={filter === id} onChange={() => setFilter(id)} />{label}</label>))}
      </div>
      <table className="fv-table" aria-label="Định giá tham khảo">
        <thead><tr><th>Mã</th><th>Ngành</th><th className="num">Giá</th><th className="num">Giá hợp lý</th><th className="num">Chênh lệch</th><th>Kết luận</th><th>Chất lượng</th><th>Số liệu</th><th /></tr></thead>
        <tbody>{rows.map((r) => (
          <Fragment key={r.symbol}>
            <tr>
              <td data-label="Mã"><Link href={`/research/${r.symbol}`}><strong>{r.symbol}</strong></Link>{r.held && <> <span className="pill good">Đang nắm</span></>}</td>
              <td data-label="Ngành">{r.sector}</td>
              <td data-label="Giá" className="num">{formatVnd(r.price)}</td>
              <td data-label="Giá hợp lý" className="num">{r.fair ? <>{formatVnd(r.fair)}<div className="caption">{formatVnd(r.low, { unit: false })} – {formatVnd(r.high, { unit: false })}</div></> : "—"}</td>
              <td data-label="Chênh lệch" className="num">{r.gap ? signedPct(r.gap) : "—"}</td>
              <td data-label="Kết luận"><span className={`pill ${VERDICT[r.verdict].tone}`}>{VERDICT[r.verdict].label}</span>{r.reason && <div className="caption">{r.reason}</div>}</td>
              <td data-label="Chất lượng"><FScoreCell q={r.quality} /></td>
              <td data-label="Số liệu">{r.latest_quarter ?? "—"}{r.new_quarter && <> <span className="pill warn">Quý mới</span></>}</td>
              <td><button className="btn" aria-expanded={open === r.symbol} onClick={() => setOpen(open === r.symbol ? null : r.symbol)}
                aria-label={`Chi tiết ${r.symbol}`}>Chi tiết</button></td>
            </tr>
            {open === r.symbol && <tr className="fv-detail"><td colSpan={9}>
              <MethodList row={r} />
              <QualityList symbol={r.symbol} q={r.quality} />
              <MultipleCharts symbol={r.symbol} />
            </td></tr>}
          </Fragment>))}
        </tbody>
      </table>
    </section>
  );
}
