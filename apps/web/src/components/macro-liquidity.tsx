"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { bandSpot } from "../lib/macro-extras";

type Obs = { date: string; value: string } | null;
type Fx = { latest: Obs; ceiling: string | null; floor: string | null; band?: string; vcb: Obs; room: string | null; near_ceiling: boolean | null;
  ytd: { from: string; value: string; change: string } | null; ytd_missing: string | null };
type Row = { kind: string; group: string; term_days: number; members: string; volume: string; rate: string };
type Omo = { latest: { date: string; inject: string; absorb: string; rows: Row[] } | null; history: { date: string; inject: string; absorb: string }[];
  complete: boolean; outstanding: { repo: string; bill: string; net: string } | null; net: string | null; maturing_7d: string | null; missing_reason: string | null };
type Liquidity = { fx: Fx; omo: Omo; interbank: { terms: { id: string; date: string; value: string }[]; jump: { from: string; change: string } | null };
  external: Record<"vn_trade_balance" | "vn_trade_balance_ytd" | "vn_fdi_disbursed" | "vn_fdi_disbursed_yoy", Obs> };

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const num = (v: string | number, digits = 2) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: digits });
const pct = (ratio: string, digits = 2) => `${(Number(ratio) * 100).toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
const signed = (v: string, digits = 2) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${num(Math.abs(Number(v)), digits)}`;
const month = (iso: string) => `${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const TERM: Record<string, string> = { vn_interbank_on: "Qua đêm", vn_interbank_1w: "1 tuần", vn_interbank_1m: "1 tháng" };
const KIND: Record<string, string> = { repo: "bơm (mua kỳ hạn)", outright: "bơm (mua hẳn)", bill: "hút (tín phiếu)", reverse: "hút (bán kỳ hạn)" };

/** V2, V4 and V3 on Vĩ mô: the central rate and its band, the open market with interbank rates, and the month's trade and FDI. */
export function MacroLiquidity() {
  const [d, setD] = useState<Liquidity | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Liquidity>("macro/liquidity").then(setD, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const state = <>{error && <p className="errors" role="alert">{error}</p>}{!d && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}</>;
  return (
    <>
      <section className="surface" aria-label="Tỷ giá trung tâm và biên độ">
        <h2>Tỷ giá trung tâm và biên độ</h2>
        <p className="caption">Ngân hàng chỉ được bán USD trong biên độ ±5% quanh tỷ giá trung tâm của NHNN. Tỷ giá bán của Vietcombank càng gần trần thì
          áp lực tỷ giá càng lớn; dưới 1% là sát trần.</p>
        {state}
        {d && (d.fx.latest ? <FxBand fx={d.fx} /> : <p className="muted">Chưa có tỷ giá trung tâm.</p>)}
      </section>
      <section className="surface" aria-label="Thanh khoản hệ thống">
        <h2>Thanh khoản hệ thống (thị trường mở)</h2>
        <p className="caption">NHNN bơm tiền qua mua kỳ hạn giấy tờ có giá (đến hạn thì tiền quay về) và hút tiền qua bán tín phiếu. Trang NHNN chỉ hiện phiên
          mới nhất, nên lịch sử là các phiên ứng dụng đã lưu từ mỗi lượt cập nhật.</p>
        {state}
        {d && <OmoView omo={d.omo} interbank={d.interbank} />}
      </section>
      <section className="surface" aria-label="Cán cân ngoại tệ">
        <h2>Cán cân ngoại tệ hằng tháng</h2>
        <p className="caption">Xuất siêu và vốn FDI giải ngân là nguồn cung USD chính; nhập siêu kéo dài làm tăng cầu USD. Số từ báo cáo kinh tế – xã hội tháng
          của Cục Thống kê (sơ bộ).</p>
        {state}
        {d && <External e={d.external} />}
      </section>
    </>
  );
}

function FxBand({ fx }: { fx: Fx }) {
  const spot = bandSpot(fx.vcb?.value ?? null, fx.floor!, fx.ceiling!);
  return <>
    {fx.near_ceiling && <p className="notice" role="status">Tỷ giá Vietcombank chỉ còn cách trần {pct(fx.room!)}.</p>}
    <p data-testid="fx-central"><strong>{num(fx.latest!.value, 0)} đ/USD</strong> <span className="caption">tỷ giá trung tâm áp dụng ngày {dmy(fx.latest!.date)}</span></p>
    <ul className="perf-bench">
      <li>Biên độ: sàn {num(fx.floor!, 0)} – trần {num(fx.ceiling!, 0)} đ/USD</li>
      <li>Vietcombank bán: {fx.vcb ? <>{num(fx.vcb.value, 0)} đ ngày {dmy(fx.vcb.date)}, <strong>còn {pct(fx.room!)} tới trần</strong></> : <span className="muted">chưa có số cùng tuần để so</span>}</li>
      <li>Từ đầu năm: {fx.ytd ? <>{signed(String(Number(fx.ytd.change) * 100))}% (từ {num(fx.ytd.value, 0)} đ ngày {dmy(fx.ytd.from)})</> : <span className="muted">{fx.ytd_missing}</span>}</li>
    </ul>
    {spot !== null && <div className="band-bar" role="img" aria-label={`Vietcombank ở ${Math.round(spot * 100)}% biên độ, từ sàn đến trần`}>
      <span className="band-mid" /><span className="band-dot" style={{ left: `${spot * 100}%` }} />
      <span className="band-lab band-l">Sàn</span><span className="band-lab band-c">Trung tâm</span><span className="band-lab band-r">Trần</span>
    </div>}
  </>;
}

function OmoView({ omo, interbank }: { omo: Omo; interbank: Liquidity["interbank"] }) {
  const l = omo.latest;
  return <>
    {interbank.jump && <p className="notice" role="status">Lãi suất liên ngân hàng qua đêm tăng {num(interbank.jump.change)} điểm % trong 5 phiên (từ {dmy(interbank.jump.from)}).</p>}
    {interbank.terms.length > 0 && <p data-testid="interbank-terms"><strong>Liên ngân hàng:</strong>{" "}
      {interbank.terms.map((t) => `${TERM[t.id]} ${num(t.value)}%`).join(" · ")} <span className="caption">(ngày {dmy(interbank.terms[0].date)})</span></p>}
    {!l ? <p className="muted">{omo.missing_reason}</p> : <>
      <p data-testid="omo-latest"><strong>Phiên {dmy(l.date)}: bơm {num(l.inject, 0)} tỷ đ{Number(l.absorb) > 0 ? `, hút ${num(l.absorb, 0)} tỷ đ` : ""}</strong></p>
      <table className="fv-table" aria-label="Kết quả thị trường mở phiên mới nhất">
        <thead><tr><th>Loại</th><th className="num">Kỳ hạn</th><th className="num">Trúng thầu</th><th className="num">Khối lượng (tỷ đ)</th><th className="num">Lãi suất</th></tr></thead>
        <tbody>{l.rows.filter((r) => Number(r.volume) > 0).map((r) => <tr key={`${r.kind}-${r.term_days}`}>
          <td data-label="Loại">{KIND[r.kind] ?? r.group}</td><td className="num" data-label="Kỳ hạn">{r.term_days} ngày</td>
          <td className="num" data-label="Trúng thầu">{r.members}</td><td className="num" data-label="Khối lượng">{num(r.volume)}</td>
          <td className="num" data-label="Lãi suất">{num(r.rate)}%</td></tr>)}</tbody>
      </table>
      <ul className="perf-bench">
        <li>Đến hạn 7 ngày tới (từ các phiên đã lưu): {num(omo.maturing_7d ?? "0", 0)} tỷ đ</li>
        {omo.complete ? <><li>Bơm/hút ròng phiên này: <strong>{signed(omo.net!, 0)} tỷ đ</strong></li>
          <li>Số dư đang lưu hành: mua kỳ hạn {num(omo.outstanding!.repo, 0)} tỷ đ, tín phiếu {num(omo.outstanding!.bill, 0)} tỷ đ</li></>
          : <li className="muted">{omo.missing_reason}</li>}
      </ul>
      {omo.history.length > 1 && <p className="caption">Đã lưu {omo.history.length} phiên, từ {dmy(omo.history[0].date)}.</p>}
    </>}
  </>;
}

function External({ e }: { e: Liquidity["external"] }) {
  const tb = e.vn_trade_balance, ytd = e.vn_trade_balance_ytd, fdi = e.vn_fdi_disbursed, yoy = e.vn_fdi_disbursed_yoy;
  const balance = (o: Obs) => !o ? <span className="muted">chưa có số</span>
    : <><strong className={Number(o.value) < 0 ? "negative" : "positive"}>{Number(o.value) < 0 ? "nhập siêu" : "xuất siêu"} {num(Math.abs(Number(o.value)))} tỷ USD</strong>
      <span className="caption"> (tháng {month(o.date)})</span></>;
  return <ul className="perf-bench" aria-label="Cán cân và FDI">
    <li>Cán cân thương mại trong tháng: {balance(tb)}</li>
    <li>Cán cân từ đầu năm: {balance(ytd)}</li>
    <li>FDI giải ngân từ đầu năm: {fdi ? <><strong>{num(fdi.value)} tỷ USD</strong>{yoy && yoy.date === fdi.date ? ` (${signed(yoy.value, 1)}% so cùng kỳ)` : ""}
      <span className="caption"> (đến tháng {month(fdi.date)})</span></> : <span className="muted">chưa có số</span>}</li>
  </ul>;
}
