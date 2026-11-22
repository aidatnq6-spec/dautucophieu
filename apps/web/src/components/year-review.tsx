"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd, hanoiDate } from "../lib/format";

type Err = { error: string };
type Portfolio = { return: string | null; vnindex?: string | null; start?: { date: string; value: string } | null; end?: { date: string; value: string } | null; note?: string | null };
type Flows = { deposits: string; withdrawals: string; net: string; dividends: string; tax_withheld: string; realized: string };
type Contrib = { months: number; met: number; planned: string; put_in: string } | null;
type Cash = { months: number; missing: string[]; income: string | null; spending: string | null; saved: string | null; rate: string | null };
type Layer = { id: string; share: string | null; target_min: string; target_max: string; status: string };
type Tower = { start: { total: string } | null; end: { total: string; taken_on: string } | null; end_month: string | null; now: Layer[]; note: string | null };
export type Review = { year: number; as_of: string; running: boolean; portfolio: Portfolio | Err; flows: Flows | Err; contributions: Contrib | Err;
  cashflow: Cash | Err; tower: Tower | Err };

const LAYER: Record<string, string> = { deposit: "Tiền gửi", bond: "Trái phiếu", gold: "Vàng", stocks: "Cổ phiếu", crypto: "Tiền số" };
const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const mm = (key: string) => `${key.slice(5, 7)}/${key.slice(0, 4)}`;
const isErr = (v: unknown): v is Err => !!v && typeof v === "object" && "error" in v;

/** A share as a percentage with one decimal, signed or not; "—" when missing. */
export function pctText(v: string | null | undefined, signed = true): string {
  if (v === null || v === undefined) return "—";
  const x = Number(v) * 100;
  const body = Math.abs(x).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const sign = x < 0 ? "−" : signed && x > 0 ? "+" : "";
  return `${sign}${body}%`;
}

/** The months of Thu chi hằng tháng not entered, by name; never filled in. */
export function missingText(missing: string[]): string | null {
  return missing.length ? `chưa nhập ${missing.length} tháng: ${missing.map(mm).join(", ")}` : null;
}

function Part({ title, value, children }: { title: string; value: unknown; children: React.ReactNode }) {
  return (
    <div className="yr-part">
      <h3>{title}</h3>
      {isErr(value) ? <p className="caption">{value.error}</p> : children}
    </div>
  );
}

function PortfolioPart({ p }: { p: Portfolio }) {
  if (p.return === null) return <p className="caption">{p.note}</p>;
  return (
    <>
      <p><strong className={Number(p.return) >= 0 ? "positive" : "negative"}>{pctText(p.return)}</strong> so với VN-Index {pctText(p.vnindex)}
        <span className="caption"> (đã trừ tiền nộp, rút)</span></p>
      {p.start && p.end && <p className="caption">Giá trị {formatVnd(p.start.value)} ngày {dmy(p.start.date)} → {formatVnd(p.end.value)} ngày {dmy(p.end.date)}</p>}
      {p.note && <p className="caption">{p.note}</p>}
    </>
  );
}

function TowerPart({ t }: { t: Tower }) {
  return (
    <>
      {t.start && t.end ? <p>Tổng tài sản {formatVnd(t.start.total)} → {formatVnd(t.end.total)} (cuối {mm(t.end_month!)})</p>
        : t.end ? <p>Tổng tài sản cuối {mm(t.end_month!)}: {formatVnd(t.end.total)}</p> : null}
      {t.note && <p className="caption">{t.note}</p>}
      {t.now.length > 0 && <ul className="yr-layers">{t.now.map((l) => <li key={l.id}>{LAYER[l.id] ?? l.id}: {pctText(l.share, false)}
        <span className="caption"> (mục tiêu {pctText(l.target_min, false)}–{pctText(l.target_max, false)})</span></li>)}</ul>}
    </>
  );
}

/** Tổng kết năm: every figure from a part the app already has, for one year; what is missing is named. */
export function YearReview() {
  const thisYear = Number(hanoiDate().slice(0, 4));
  const [year, setYear] = useState(thisYear);
  const [data, setData] = useState<Review | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<Review>(`year-review/${year}`).then((d) => { setData(d); setMessage(null); }, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [year]);
  const r = data && data.year === year ? data : null;
  return (
    <section className="surface" aria-label="Tổng kết năm">
      <h2>Tổng kết năm {year}</h2>
      <div className="chips" role="radiogroup" aria-label="Năm">
        {[thisYear - 1, thisYear].map((y) => <button key={y} type="button" role="radio" aria-checked={year === y} className={`chip${year === y ? " on" : ""}`}
          onClick={() => setYear(y)}>{y}</button>)}
      </div>
      {message && <p className="errors" role="alert">{message}</p>}
      {!r && !message && <p className="muted" role="status">Đang tải…</p>}
      {r && <>
        {r.running && <p className="caption">Năm đang chạy: tính đến {dmy(r.as_of)}.</p>}
        <div className="yr-grid">
          <Part title="Danh mục cổ phiếu" value={r.portfolio}>{!isErr(r.portfolio) && <PortfolioPart p={r.portfolio} />}</Part>
          <Part title="Tiền vào, ra, cổ tức" value={r.flows}>{!isErr(r.flows) && <dl className="yr-dl">
            <dt>Nộp</dt><dd>{formatVnd(r.flows.deposits)}</dd>
            <dt>Rút</dt><dd>{formatVnd(r.flows.withdrawals)}</dd>
            <dt>Cổ tức tiền đã nhận</dt><dd>{formatVnd(r.flows.dividends)}</dd>
            <dt>Thuế đã khấu trừ</dt><dd>{formatVnd(r.flows.tax_withheld)}</dd>
            <dt>Lãi, lỗ đã chốt</dt><dd>{formatVnd(r.flows.realized)}</dd></dl>}</Part>
          <Part title="Góp vốn đều" value={r.contributions}>{!isErr(r.contributions) && (r.contributions
            ? <p>{r.contributions.met}/{r.contributions.months} tháng đủ · đã góp {formatVnd(r.contributions.put_in)} / kế hoạch {formatVnd(r.contributions.planned)}</p>
            : <p className="caption">Chưa đặt Góp vốn đều, hoặc năm này chưa có tháng nào trong kế hoạch.</p>)}</Part>
          <Part title="Thu chi cả năm" value={r.cashflow}>{!isErr(r.cashflow) && <>
            {r.cashflow.months
              ? <p>{r.cashflow.months} tháng: thu {formatVnd(r.cashflow.income ?? "0")}, chi {formatVnd(r.cashflow.spending ?? "0")}, để dành {formatVnd(r.cashflow.saved ?? "0")} ({pctText(r.cashflow.rate, false)})</p>
              : <p className="caption">Chưa có tháng nào đã xong của năm này.</p>}
            {missingText(r.cashflow.missing) && <p className="caption">{missingText(r.cashflow.missing)}</p>}</>}</Part>
          <Part title="Tháp tài sản" value={r.tower}>{!isErr(r.tower) && <TowerPart t={r.tower} />}</Part>
        </div>
      </>}
    </section>
  );
}
