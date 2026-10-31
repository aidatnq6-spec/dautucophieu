"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";
import { EventTable, type Ev } from "./events-view";
import { MethodList, VERDICT, type Row } from "./fair-value-view";
import { SOURCE } from "./insights-view";
import { MultipleCharts } from "./multiple-chart";
import { QualityList } from "./report-quality";
import { BankFigures } from "./bank-figures";
import { ForwardValuation } from "./forward-valuation";
import { SectorRatios } from "./sector-ratios";
import { DividendHistory } from "./dividend-history";
import { CapmTicker } from "./capm";
import { CompanyPeople } from "./company-people";

type Facts = { price: string | null; price_date: string | null; change_pct: string | null; high_52w: string | null; low_52w: string | null;
  shares: number | null; market_cap: string | null; avg_volume: number | null; avg_volume_sessions: number };
type Claim = { effect: "benefit" | "harm"; reason: string; quote: string; page: number; source: string; url: string };
type Sector = { sector: string; benefit: number; harm: number; mixed: boolean; claims: Claim[] };
export type Profile = { symbol: string; sector: string | null; watched: boolean; held: boolean; facts: Facts; valuation: Row | null;
  events: { upcoming: Ev[]; past: Ev[]; undated: Ev[]; insider: Ev[] }; insights: { sector: Sector | null; window_days: number } };

const day = (iso: string) => iso.split("-").reverse().join("/");
const count = (n: number) => n.toLocaleString("vi-VN");
/** Đồng as a decimal string → tỷ đồng, on the string itself. */
const billions = (v: string) => `${formatDecimal(v.length > 9 ? `${v.slice(0, -9)}.${v.slice(-9)}` : `0.${v.padStart(9, "0")}`, 0)} tỷ`;

function Fact({ label, children, note }: { label: string; children: React.ReactNode; note?: string }) {
  return <div><span className="kpi-label">{label}</span><strong>{children}</strong>{note && <span className="caption">{note}</span>}</div>;
}

/** Quick facts, reference valuation, events and sector insights of one ticker, from data the other pages already keep. */
export function StockProfile({ symbol }: { symbol: string }) {
  const [p, setP] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [insider, setInsider] = useState(false);
  useEffect(() => {
    api<Profile>(`stock/${encodeURIComponent(symbol)}`).then(setP, (e) => setError(e instanceof ApiError ? e.failure.message : "Không tải được hồ sơ."));
  }, [symbol]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!p) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const f = p.facts, v = p.valuation, s = p.insights.sector;
  return (
    <>
      <section className="surface" aria-label="Thông tin nhanh">
        <div className="kpi-row">
          <Fact label="Giá" note={f.price_date ? `phiên ${day(f.price_date)}` : undefined}>{formatVnd(f.price)}</Fact>
          <Fact label="Thay đổi phiên">{f.change_pct ? <span className={!/[1-9]/.test(f.change_pct) ? "" : f.change_pct.startsWith("-") ? "negative" : "positive"}>
            {f.change_pct.startsWith("-") || !/[1-9]/.test(f.change_pct) ? "" : "+"}{formatRatio(f.change_pct, 2)}</span> : "—"}</Fact>
          <Fact label="Cao / thấp 52 tuần" note="giá đóng cửa đã điều chỉnh">
            {f.high_52w && f.low_52w ? `${formatVnd(f.high_52w, { unit: false })} / ${formatVnd(f.low_52w, { unit: false })}` : "—"}</Fact>
          <Fact label="Vốn hoá" note="giá × số cổ phiếu ước tính">{f.market_cap ? billions(f.market_cap) : "—"}</Fact>
          <Fact label="Số cổ phiếu" note="ước tính từ lợi nhuận / EPS">{f.shares ? count(f.shares) : "—"}</Fact>
          <Fact label={`KLGD TB ${f.avg_volume_sessions || 20} phiên`}>{f.avg_volume !== null ? count(f.avg_volume) : "—"}</Fact>
        </div>
      </section>

      <section className="surface" aria-label="Định giá tham khảo">
        <h2>Định giá tham khảo</h2>
        {!p.watched ? <p className="muted">Chỉ định giá các mã trong danh sách theo dõi (data\market-symbols.txt).</p> : !v ? <p className="muted">Chưa có định giá.</p> : <>
          <p><span className={`pill ${VERDICT[v.verdict].tone}`}>{VERDICT[v.verdict].label}</span>{" "}
            {v.fair ? <>Giá hợp lý {formatVnd(v.fair)} ({formatVnd(v.low, { unit: false })} – {formatVnd(v.high, { unit: false })})
              {v.gap && <>, giá hiện tại {v.gap.startsWith("-") ? "thấp hơn" : "cao hơn"} {formatRatio(v.gap.replace("-", ""), 1)}</>}</> : v.reason}
            {v.latest_quarter && <span className="caption"> · số liệu {v.latest_quarter}</span>}</p>
          <MethodList row={v} />
          <QualityList symbol={p.symbol} q={v.quality} />
          <CapmTicker symbol={p.symbol} />
          <MultipleCharts symbol={p.symbol} />
          <p className="caption"><Link href="/fair-value">So sánh với các mã khác ở Định giá</Link></p>
        </>}
      </section>

      {p.watched && <ForwardValuation symbol={p.symbol} />}

      {p.watched && <SectorRatios symbol={p.symbol} />}

      {p.watched && <BankFigures symbol={p.symbol} />}

      {p.watched && <DividendHistory symbol={p.symbol} />}

      {p.watched && <CompanyPeople symbol={p.symbol} />}

      <section className="surface" aria-label="Sự kiện">
        <h2>Sự kiện</h2>
        <h3>Sắp tới</h3><EventTable label={`Sự kiện sắp tới của ${p.symbol}`} rows={p.events.upcoming} symbol={false} />
        <h3>12 tháng qua</h3><EventTable label={`Sự kiện đã qua của ${p.symbol}`} rows={p.events.past} symbol={false} />
        {p.events.undated.length > 0 && <><h3>Chưa có ngày</h3><EventTable label={`Sự kiện chưa có ngày của ${p.symbol}`} rows={p.events.undated} symbol={false} /></>}
        {p.events.insider.length > 0 && <>
          <button className="btn" aria-expanded={insider} onClick={() => setInsider(!insider)}>
            {insider ? "Ẩn" : "Xem"} giao dịch nội bộ 90 ngày qua ({p.events.insider.length})</button>
          {insider && <EventTable label={`Giao dịch nội bộ của ${p.symbol}`} rows={p.events.insider} symbol={false} />}</>}
      </section>

      <section className="surface" aria-label="Nhận định về ngành">
        <h2>Nhận định về ngành{p.sector ? `: ${p.sector}` : ""}</h2>
        {!s ? <p className="muted">Không có báo cáo nào trong {p.insights.window_days} ngày qua nói về ngành này.</p> : <>
          <p>{s.benefit} nhận định hưởng lợi, {s.harm} nhận định bất lợi trong {p.insights.window_days} ngày qua
            {s.mixed && <> <span className="pill warn">Các nguồn khác ý</span></>}.</p>
          <ul>{s.claims.map((c, i) => (
            <li key={i} className="ins-claim"><span className={`pill ${c.effect === "benefit" ? "good" : "bad"}`}>{c.effect === "benefit" ? "Hưởng lợi" : "Bất lợi"}</span>
              {" "}{c.reason} <span className="caption">— <a href={c.url} target="_blank" rel="noreferrer">{SOURCE[c.source] ?? c.source}, tr. {c.page}</a> «{c.quote}»</span></li>))}
          </ul>
          <p className="caption"><Link href="/insights">Xem toàn bộ ở Nhận định</Link></p>
        </>}
      </section>
    </>
  );
}
