"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Row = { symbol: string; sector: string | null; held: boolean; reported: boolean; npat: string | null; yoy: string | null; qoq: string | null; ytd: string | null;
  ytd_yoy: string | null; plan_ratio: string | null; plan_label: string | null; forecast: string | null; vs_forecast: string | null; seasonal_share: string | null; review: string | null };
type Sector = { sector: string; count: number; reported: number; compared: number; ytd_growth: string | null; up: number; down: number; top: string | null; top_share: string | null;
  ytd_growth_without_top: string | null };
type Cash = { symbol: string; npat: string; cfo: string; ratio: string | null; kind: "paper_profit" | "cash_above" | null; other_liabilities_change: string | null };
type Review = { symbol: string; quarter: string; verdict: string; note: string; at: string };
type View = { quarter: string | null; label?: string; version: number; rows: Row[]; sectors: Sector[]; cash: Cash[]; reviews: Review[]; verdicts: Record<string, string>;
  watched: number; reported: number };

const ty = (v: string | null) => (v === null ? "—" : `${(Number(v) / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tỷ`);
const pct = (v: string | null) => (v === null ? "—" : `${Number(v) > 0 ? "+" : ""}${formatRatio(v, 1)}`);
const tone = (v: string | null) => (v === null ? undefined : Number(v) > 0 ? "positive" : Number(v) < 0 ? "negative" : undefined);
const qLabel = (q: string) => `Q${q.slice(-1)}/${q.slice(0, 4)}`;

/** Mùa báo cáo: the watched tickers' latest quarter, sectors with and without their biggest mover, profit against cash, and the owner's review of held tickers. */
export function EarningsView() {
  const [view, setView] = useState<View | null>(null);
  const [onlyHeld, setOnlyHeld] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, { verdict: string; note: string }>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("earnings").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function saveReview(symbol: string) {
    if (!view?.quarter) return;
    const d = drafts[symbol];
    if (!d?.verdict) { setMessage(`Chọn kết luận cho ${symbol}.`); return; }
    setBusy(true);
    try {
      setView(await api<View>("earnings/reviews", { method: "PUT", body: { symbol, quarter: view.quarter, verdict: d.verdict, note: d.note ?? "", expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
    finally { setBusy(false); }
  }
  if (message && !view) return <p className="errors" role="alert">{message}</p>;
  if (!view) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  if (!view.quarter) return <p className="muted">Chưa có báo cáo quý nào của danh sách theo dõi.</p>;
  const rows = view.rows.filter((r) => !onlyHeld || r.held);
  const held = view.rows.filter((r) => r.held && r.reported);
  const flagged = view.cash.filter((c) => c.kind);
  return (
    <>
      <section className="surface" aria-label="Kết quả từng mã">
        <h2>Kết quả {view.label}: {view.reported}/{view.watched} mã đã có báo cáo</h2>
        <p className="caption">Lợi nhuận sau thuế công ty mẹ, từ báo cáo công khai đã lưu. Lũy kế là từ đầu năm đến {view.label}. Kế hoạch năm và dự phóng là số bạn nhập ở trang từng mã (hoặc kế hoạch CafeF). “Quý này thường chiếm” là tỷ trọng trung bình của quý này trong lợi nhuận cả năm, tối đa 3 năm trước: quý nhỏ thì đừng vội kết luận cả năm. Không phải khuyến nghị.</p>
        <label className="db-check"><input type="checkbox" checked={onlyHeld} onChange={(e) => setOnlyHeld(e.target.checked)} /> Chỉ mã đang nắm</label>
        <div className="tablewrap"><table className="fv-table" aria-label={`Kết quả ${view.label}`}>
          <thead><tr><th>Mã</th><th>Ngành</th><th className="num">LNST quý</th><th className="num">So cùng kỳ</th><th className="num">So quý trước</th><th className="num">Lũy kế so cùng kỳ</th>
            <th className="num">% kế hoạch năm</th><th className="num">So dự phóng của bạn</th><th className="num">Quý này thường chiếm</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.symbol} data-testid={`er-${r.symbol}`}>
            <td data-label="Mã"><Link href={`/research/${r.symbol}`}><strong>{r.symbol}</strong></Link>{r.held && <span className="pill">đang nắm</span>}</td>
            <td data-label="Ngành">{r.sector ?? "—"}</td>
            <td data-label="LNST quý" className="num">{r.reported ? ty(r.npat) : <span className="muted">chưa có</span>}</td>
            <td data-label="So cùng kỳ" className={`num ${tone(r.yoy) ?? ""}`}>{pct(r.yoy)}</td><td data-label="So quý trước" className={`num ${tone(r.qoq) ?? ""}`}>{pct(r.qoq)}</td>
            <td data-label="Lũy kế so cùng kỳ" className={`num ${tone(r.ytd_yoy) ?? ""}`}>{pct(r.ytd_yoy)}</td>
            <td data-label="% kế hoạch năm" className="num">{r.plan_ratio ? `${formatRatio(r.plan_ratio, 0)}${r.plan_label && r.plan_label !== "LNST" ? ` (${r.plan_label})` : ""}` : "—"}</td>
            <td data-label="So dự phóng của bạn" className={`num ${tone(r.vs_forecast) ?? ""}`}>{r.vs_forecast ? `${Number(r.vs_forecast) >= 0 ? "hơn" : "kém"} ${formatRatio(String(Math.abs(Number(r.vs_forecast))), 0)}` : "—"}</td>
            <td data-label="Quý này thường chiếm" className="num">{r.seasonal_share ? formatRatio(r.seasonal_share, 0) : "—"}</td></tr>)}</tbody>
        </table></div>
      </section>

      <section className="surface" aria-label="Tăng trưởng theo ngành">
        <h2>Tăng trưởng theo ngành (lũy kế từ đầu năm)</h2>
        <p className="caption">Cộng lợi nhuận các mã trong danh sách theo dõi có đủ số của cả hai năm (không phải toàn thị trường). Một ngành tăng mạnh có thể chỉ nhờ một mã: cột cuối là tăng trưởng của ngành khi bỏ mã đóng góp lớn nhất.</p>
        <div className="tablewrap"><table className="fv-table" aria-label="Tăng trưởng theo ngành">
          <thead><tr><th>Ngành</th><th className="num">Mã có số</th><th className="num">Lũy kế so cùng kỳ</th><th className="num">Tăng / giảm</th><th>Đóng góp lớn nhất</th><th className="num">Bỏ mã đó</th></tr></thead>
          <tbody>{view.sectors.map((s) => <tr key={s.sector} data-testid={`es-${s.sector}`}><td data-label="Ngành">{s.sector}</td><td data-label="Mã có số" className="num">{s.compared}/{s.count}</td>
            <td data-label="Lũy kế so cùng kỳ" className={`num ${tone(s.ytd_growth) ?? ""}`}>{pct(s.ytd_growth)}</td><td data-label="Tăng / giảm" className="num">{s.up} / {s.down}</td>
            <td data-label="Đóng góp lớn nhất">{s.top ? `${s.top}${s.top_share ? ` · ${formatRatio(s.top_share, 0)} phần tăng` : ""}` : "—"}</td>
            <td data-label="Bỏ mã đó" className={`num ${tone(s.ytd_growth_without_top) ?? ""}`}>{pct(s.ytd_growth_without_top)}</td></tr>)}</tbody>
        </table></div>
      </section>

      <section className="surface" aria-label="Lợi nhuận và dòng tiền">
        <h2>Lợi nhuận và dòng tiền (lũy kế từ đầu năm)</h2>
        <p className="caption">So lợi nhuận sau thuế với dòng tiền thuần từ hoạt động kinh doanh. “Lãi chưa thành tiền”: có lãi nhưng tiền kinh doanh âm (thường do tồn kho, phải thu tăng). “Tiền vượt xa lợi nhuận”: tiền từ 2 lần lợi nhuận trở lên, có thể do nhận đặt cọc, trả chậm hoặc trích trước chi phí. Nguồn chỉ có tổng các khoản nợ, nên cột cuối là “nợ phải trả ngoài vay” (phải trả, đặt cọc, trích trước, dự phòng) thay đổi từ cuối năm trước: chi tiết xem thuyết minh. Không áp dụng cho ngân hàng, chứng khoán, bảo hiểm. Là dấu hiệu để đọc kỹ, không phải kết luận.</p>
        {flagged.length === 0 ? <p className="muted">Chưa mã nào có dấu hiệu theo ngưỡng trên.</p> : <div className="tablewrap"><table className="fv-table" aria-label="Lợi nhuận và dòng tiền">
          <thead><tr><th>Mã</th><th>Dấu hiệu</th><th className="num">LNST</th><th className="num">Dòng tiền KD</th><th className="num">Tiền / lãi</th><th className="num">Nợ phải trả ngoài vay</th></tr></thead>
          <tbody>{flagged.map((c) => <tr key={c.symbol} data-testid={`ec-${c.symbol}`}><td data-label="Mã"><Link href={`/research/${c.symbol}`}>{c.symbol}</Link></td>
            <td data-label="Dấu hiệu"><span className={`pill ${c.kind === "paper_profit" ? "bad" : "warn"}`}>{c.kind === "paper_profit" ? "Lãi chưa thành tiền" : "Tiền vượt xa lợi nhuận"}</span></td>
            <td data-label="LNST" className="num">{ty(c.npat)}</td><td data-label="Dòng tiền KD" className={`num ${tone(c.cfo) ?? ""}`}>{ty(c.cfo)}</td>
            <td data-label="Tiền / lãi" className="num">{c.ratio ? `${Number(c.ratio).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} lần` : "—"}</td>
            <td data-label="Nợ phải trả ngoài vay" className={`num ${tone(c.other_liabilities_change) ?? ""}`}>{c.other_liabilities_change === null ? "—" : `${Number(c.other_liabilities_change) > 0 ? "+" : ""}${ty(c.other_liabilities_change)}`}</td></tr>)}</tbody>
        </table></div>}
      </section>

      <section className="surface" id="ra-soat" aria-label="Rà luận điểm sau báo cáo">
        <h2>Rà luận điểm sau báo cáo {view.label}</h2>
        <p className="caption">Với mỗi mã đang nắm đã có báo cáo, ghi kết luận của bạn sau khi đọc số: giữ luận điểm, theo dõi thêm hay xem lại. Mã chưa rà được nhắc ở Việc cần xem. Luận điểm và điều kiện ở <Link href="/portfolio">Danh mục & Giao dịch</Link>. Phần mềm không kết luận thay bạn.</p>
        {message && <p className="errors" role="alert">{message}</p>}
        {held.length === 0 ? <p className="muted">Không có mã đang nắm nào đã ra báo cáo {view.label}.</p> : <div className="tablewrap"><table className="fv-table" aria-label="Kết luận sau báo cáo">
          <thead><tr><th>Mã</th><th className="num">So cùng kỳ</th><th>Kết luận</th><th>Ghi chú</th><th /></tr></thead>
          <tbody>{held.map((r) => {
            const d = drafts[r.symbol] ?? { verdict: r.review ?? "", note: "" };
            return <tr key={r.symbol} data-testid={`rv-${r.symbol}`}><td data-label="Mã"><strong>{r.symbol}</strong>{r.review ? <span className="pill good">đã rà</span> : <span className="pill warn">chưa rà</span>}</td>
              <td data-label="So cùng kỳ" className={`num ${tone(r.yoy) ?? ""}`}>{pct(r.yoy)}</td>
              <td data-label="Kết luận"><select aria-label={`Kết luận ${r.symbol}`} value={d.verdict} disabled={busy} onChange={(e) => setDrafts({ ...drafts, [r.symbol]: { ...d, verdict: e.target.value } })}>
                <option value="">Chọn…</option>{Object.entries(view.verdicts).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
              <td data-label="Ghi chú"><input aria-label={`Ghi chú ${r.symbol}`} maxLength={500} value={d.note} disabled={busy} onChange={(e) => setDrafts({ ...drafts, [r.symbol]: { ...d, note: e.target.value } })} /></td>
              <td className="db-actions"><button type="button" className="btn" disabled={busy} aria-label={`Lưu kết luận ${r.symbol}`} onClick={() => void saveReview(r.symbol)}><Save size={14} aria-hidden="true" />Lưu</button></td></tr>;
          })}</tbody>
        </table></div>}
        {view.reviews.length > 0 && <details className="mc-table"><summary>Các lần rà trước ({view.reviews.length})</summary>
          <ul className="er-history">{view.reviews.map((r) => <li key={`${r.symbol}-${r.quarter}`}><strong>{r.symbol}</strong> sau {qLabel(r.quarter)}: {view.verdicts[r.verdict] ?? r.verdict}{r.note ? `, ${r.note}` : ""} <span className="caption">({r.at.slice(8, 10)}/{r.at.slice(5, 7)}/{r.at.slice(0, 4)})</span></li>)}</ul>
        </details>}
      </section>
    </>
  );
}
