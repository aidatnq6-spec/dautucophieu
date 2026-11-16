"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type DebtRow = { quarter: string; debt: string | null; cash: string | null; net_debt: string | null; net_cash: boolean | null; debt_to_equity: string | null };
type Flag = { kind: "fast_borrowing" | null; quarter: string | null; debt: string | null; debt_2y_ago: string | null; ratio: string | null };
type SectorDebt = { members: number; growth_2y: string | null; compared: number; top: string | null;
  quarters: { quarter: string; count: number; debt: string | null; net_debt: string | null; net_count: number }[] };
type CashRow = { quarter: string; advances: string | null; inventory: string | null; cfo: string | null; npat_parent: string | null };
type Signal = { kind: "handover" | "collecting" | null; quarter: string | null; advances_yoy: string | null; profit_yoy: string | null };
type LiquidityRow = { quarter: string; cash: string | null; st_investments: string | null; cash_like: string | null; st_debt: string | null;
  cover: string | null; cash_share: string | null };
export type Carry = { quarter: string | null; kind: "carry" | "no_debt" | "unusual_income" | "low_interest" | null; missing: string[]; fin_income: string | null; interest: string | null;
  net: string | null; avg_cash_like: string | null; avg_debt: string | null; yield: string | null; cost: string | null; spread: string | null };
type ArRow = { quarter: string; customers: string | null; prepay: string | null; loans: string | null; other: string | null; provision: string | null;
  total: string | null; total_share: string | null; other_share: string | null; dso: string | null; prepay_days: string | null };
export type Dso = { quarter: string | null; days: string | null; year_ago: string | null; change: string | null; sector_median: string | null; sector_count: number };
export type RaiseEvent = { issue_date: string; quarter: string; capital_added: string; prepay_before: string | null; prepay_after: string | null;
  after_quarter: string; prepay_added: string | null; flag: boolean };
export type Provision = { quarter: string | null; amount: string | null; share: string | null; year_ago: string | null; kind: "jump" | "none" | null };
type Balance = { symbol: string; sector: string | null; debt: { rows: DebtRow[]; flag: Flag }; sector_debt: SectorDebt | null;
  property: { rows: CashRow[]; signal: Signal } | null; liquidity: LiquidityRow[]; carry: Carry;
  receivables: { rows: ArRow[]; dso: Dso; provision: Provision; prepay_days: Dso }; raise_prepay: { flag: boolean; events: RaiseEvent[] } };

const SHOWN = 8;  // quarters in each table
const q = (p: string) => `Q${p.slice(-1)}/${p.slice(0, 4)}`;
const ty = (v: string | null) => (v === null ? "—" : `${Math.round(Number(v) / 1e9).toLocaleString("vi-VN")} tỷ`);
const pct = (v: string) => `${Math.round(Math.abs(Number(v)) * 100).toLocaleString("vi-VN")}%`;
const move = (v: string) => `${Number(v) >= 0 ? "tăng" : "giảm"} ${pct(v)}`;

/** The warning line when borrowing at least doubled in two years; null otherwise. */
export function borrowingText(f: Flag): string | null {
  if (f.kind !== "fast_borrowing" || !f.quarter || f.debt === null) return null;
  const grew = f.ratio !== null
    ? `gấp ${Number(f.ratio).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} lần hai năm trước (${ty(f.debt_2y_ago)})`
    : "trong khi hai năm trước không vay";
  return `Nợ vay ${q(f.quarter)} là ${ty(f.debt)}, ${grew}. Vay tăng nhanh làm tăng chi phí lãi và rủi ro khi lãi suất lên: đọc thuyết minh xem vay cho dự án nào.`;
}

/** What the customer advances say about the latest quarter. */
export function advancesText(s: Signal): string {
  if (!s.quarter || s.advances_yoy === null) return "Chưa đủ số để so tiền khách trả trước với cùng kỳ năm trước.";
  if (s.kind === "handover") {
    return `${q(s.quarter)}: lợi nhuận ${s.profit_yoy !== null ? `tăng ${pct(s.profit_yoy)} so cùng kỳ` : "chuyển từ lỗ sang lãi"} trong khi tiền khách trả trước giảm ${pct(s.advances_yoy)}. `
      + "Lợi nhuận đang đến từ bàn giao những căn khách đã trả tiền trước đó, không phải từ tiền mới thu vào; xem dự án nào còn mở bán để thu tiền tiếp.";
  }
  if (s.kind === "collecting") {
    return `${q(s.quarter)}: tiền khách trả trước tăng ${pct(s.advances_yoy)} so cùng kỳ. Doanh nghiệp đã thu tiền mở bán; lợi nhuận chỉ được ghi nhận khi bàn giao, `
      + "thường sau một đến hai năm (quan sát chung của ngành, không phải dự báo cho mã này).";
  }
  return `${q(s.quarter)}: tiền khách trả trước ${move(s.advances_yoy)} so cùng kỳ: chưa rõ chiều nào. Ngưỡng của phần mềm: giảm từ 10% kèm lợi nhuận tăng từ 50% `
    + "là đang bàn giao; tăng từ 20% là đang thu tiền chờ bàn giao.";
}

const rate = (v: string) => `${(Number(v) * 100).toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;

/** Chênh lệch lãi vay – lãi gửi over the last four quarters, in words. */
export function carryText(c: Carry): string {
  if (!c.quarter) return "Báo cáo đã lưu chưa có doanh thu tài chính, nên chưa tính được.";
  if (c.missing.length) return `Chưa đủ bốn quý liên tiếp đến ${q(c.quarter)} để tính: thiếu số của ${c.missing.map(q).join(", ")}.`;
  const earned = `doanh thu tài chính ${ty(c.fin_income)} trên tiền và đầu tư ngắn hạn bình quân ${ty(c.avg_cash_like)}`
    + (c.yield !== null ? ` (khoảng ${rate(c.yield)}/năm)` : "");
  if (c.kind === "no_debt") return `Bốn quý đến ${q(c.quarter)}: không vay; ${earned}.`;
  const paid = `lãi vay ${ty(c.interest)} trên nợ vay bình quân ${ty(c.avg_debt)}${c.cost !== null ? ` (khoảng ${rate(c.cost)}/năm)` : ""}`;
  const gap = c.spread === null ? "" : ` Chênh lệch ${Number(c.spread) >= 0 ? "+" : "−"}${rate(String(Math.abs(Number(c.spread)))).replace("%", "")} điểm %.`;
  const verdict = c.kind === "carry"
    ? " Doanh nghiệp vừa vay vừa giữ nhiều tiền và thu từ tiền nhiều hơn trả lãi vay: kiểu \"vay rẻ, gửi đắt\"."
    : c.kind === "unusual_income"
      ? " Mức trên 10%/năm cao hơn mọi lãi tiền gửi: doanh thu tài chính còn gồm lãi tỷ giá, lãi bán hoặc lãi từ khoản đầu tư, cho vay; đọc thuyết minh, không coi là lãi gửi."
      : c.kind === "low_interest"
        ? " Chi phí vay dưới 2%/năm thấp hơn mọi lãi vay ngân hàng: lãi vay có thể đã được vốn hóa vào dự án hoặc tài sản dở dang (thường gặp ở bất động sản); đọc thuyết minh."
        : c.spread !== null && Number(c.spread) < 0 ? " Thu từ tiền thấp hơn chi phí vay." : "";
  return `Bốn quý đến ${q(c.quarter)}: ${earned}; ${paid}.${gap}${verdict}`;
}

/** Số ngày thu tiền of the latest quarter, against a year before and the sector. */
export function dsoText(d: Dso): string {
  if (!d.quarter || d.days === null) return "Chưa đủ phải thu khách hàng và doanh thu bốn quý để tính số ngày thu tiền.";
  const ago = d.change !== null
    ? Number(d.change) === 0 ? ", bằng cùng kỳ năm trước" : `, ${Number(d.change) > 0 ? "chậm hơn" : "nhanh hơn"} ${Math.abs(Number(d.change))} ngày so với cùng kỳ năm trước (${d.year_ago} ngày)`
    : "";
  const peers = d.sector_median !== null ? `; trung vị ngành ${d.sector_median} ngày (${d.sector_count} mã theo dõi khác)` : "";
  return `Số ngày thu tiền ${q(d.quarter)}: ${d.days} ngày${ago}${peers}.`;
}

/** Số ngày ứng trước nhà cung cấp of the latest quarter, against a year before and the sector. */
export function prepayDaysText(d: Dso): string {
  if (!d.quarter || d.days === null) return "Chưa đủ trả trước người bán và giá vốn bốn quý để tính số ngày ứng trước.";
  const ago = d.change !== null
    ? Number(d.change) === 0 ? ", bằng cùng kỳ năm trước" : `, ${Number(d.change) > 0 ? "dài hơn" : "ngắn hơn"} ${Math.abs(Number(d.change))} ngày so với cùng kỳ năm trước (${d.year_ago} ngày)`
    : "";
  const peers = d.sector_median !== null ? `; trung vị ngành ${d.sector_median} ngày (${d.sector_count} mã theo dõi khác)` : "";
  return `Số ngày ứng trước nhà cung cấp ${q(d.quarter)}: ${d.days} ngày${ago}${peers}.`;
}

/** One money-raising issue and what prepayments to suppliers did around it. */
export function raiseText(e: RaiseEvent): string {
  const day = e.issue_date.split("-").reverse().join("/");
  if (e.prepay_added === null) return `Đợt huy động vốn ngày ${day} (vốn điều lệ thêm ${ty(e.capital_added)}, ${q(e.quarter)}): thiếu số trả trước người bán để so.`;
  const moved = `trả trước người bán từ ${ty(e.prepay_before)} (trước đợt) lên ${ty(e.prepay_after)} (${q(e.after_quarter)})`;
  return e.flag
    ? `Đợt huy động vốn ngày ${day} thêm ${ty(e.capital_added)} vốn điều lệ (${q(e.quarter)}); ngay sau đó ${moved}, tăng ${ty(e.prepay_added)}, từ một nửa số vốn vừa góp. `
      + "Tiền vừa huy động có thể đã chuyển ra ngoài dưới danh nghĩa ứng trước: đọc thuyết minh xem trả trước cho ai, có phải bên liên quan không, và đã nhận hàng chưa."
    : `Đợt huy động vốn ngày ${day} thêm ${ty(e.capital_added)} vốn điều lệ (${q(e.quarter)}); ${moved}, thấp hơn một nửa số vốn vừa góp.`;
}

/** The bad-debt provision of the latest quarter, in words. */
export function provisionText(p: Provision): string {
  if (!p.quarter || p.amount === null) return "Báo cáo đã lưu chưa có dòng dự phòng phải thu khó đòi.";
  if (p.kind === "none") return `${q(p.quarter)}: không trích dự phòng phải thu ngắn hạn khó đòi.`;
  const share = p.share !== null ? `, bằng ${rate(p.share)} phải thu ngắn hạn trước dự phòng` : "";
  const jump = p.kind === "jump" ? ` Tăng mạnh so với cùng kỳ năm trước (${ty(p.year_ago)}): doanh nghiệp vừa thừa nhận thêm khoản khó thu; đọc thuyết minh xem của khách hàng nào.` : "";
  return `${q(p.quarter)}: dự phòng phải thu ngắn hạn khó đòi ${ty(p.amount)}${share}.${jump}`;
}

/** One line on the sector's borrowing. */
export function sectorText(sector: string, s: SectorDebt): string | null {
  const last = s.quarters.at(-1);
  if (!last || last.debt === null) return null;
  const net = last.net_debt !== null ? `, nợ vay ròng ${ty(last.net_debt)}${last.net_count < last.count ? ` (${last.net_count} mã)` : ""}` : "";
  const two = s.growth_2y !== null
    ? ` So với hai năm trước: ${move(s.growth_2y)} trên ${s.compared} mã có đủ số${s.top ? `, tăng nhiều nhất là ${s.top}` : ""}.`
    : " Chưa đủ số để so với hai năm trước.";
  return `Ngành ${sector} (${s.members} mã theo dõi, ${last.count} mã có số ${q(last.quarter)}): tổng nợ vay ${ty(last.debt)}${net}.${two}`;
}

export function BalanceWatch({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Balance | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<Balance>(`stock/${encodeURIComponent(symbol)}/balance`).then(setData, (e) => {
      if (e instanceof ApiError && ["not_applicable", "symbol_not_watched"].includes(e.failure.code)) return;  // banks and insurers read their own figures
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.");
    });
  }, [symbol]);
  if (message) return <section className="surface" aria-label="Nợ vay ròng"><h2>Nợ vay ròng</h2><p className="muted">{message}</p></section>;
  if (!data) return null;
  const rows = data.debt.rows.slice(-SHOWN).reverse();
  const latest = data.debt.rows.at(-1);
  const warn = borrowingText(data.debt.flag);
  const sector = data.sector && data.sector_debt ? sectorText(data.sector, data.sector_debt) : null;
  return (
    <>
      <section className="surface" aria-label="Nợ vay ròng">
        <h2>Nợ vay ròng</h2>
        {warn && <p className="notice" data-testid="borrowing-flag">{warn}</p>}
        {latest?.net_cash && <p><span className="pill good">Tiền ròng</span> {q(latest.quarter)}: tiền và đầu tư ngắn hạn nhiều hơn nợ vay {ty(String(-Number(latest.net_debt)))}.</p>}
        <table className="fv-table" aria-label={`Nợ vay ròng ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Nợ vay</th><th className="num">Tiền và đầu tư ngắn hạn</th><th className="num">Nợ vay ròng</th><th className="num">Nợ vay / vốn chủ</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Nợ vay">{ty(r.debt)}</td>
              <td className="num" data-label="Tiền và đầu tư ngắn hạn">{ty(r.cash)}</td>
              <td className={`num${r.net_cash ? " positive" : ""}`} data-label="Nợ vay ròng">{ty(r.net_debt)}</td>
              <td className="num" data-label="Nợ vay / vốn chủ">{r.debt_to_equity === null ? "—" : `${Number(r.debt_to_equity).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} lần`}</td>
            </tr>))}
          </tbody>
        </table>
        {sector && <p data-testid="sector-debt">{sector}</p>}
        <p className="caption">Nợ vay = vay ngắn hạn + vay dài hạn; nợ vay ròng = nợ vay − tiền − đầu tư ngắn hạn, âm là tiền ròng. Cảnh báo khi nợ vay gấp từ 2 lần
          tám quý trước và bằng từ 5% tổng tài sản. Báo cáo công khai (VNDirect); ô thiếu số để trống. Không phải khuyến nghị.</p>
      </section>
      <section className="surface" aria-label="Tiền và chênh lệch lãi suất">
        <h2>Tiền và chênh lệch lãi suất</h2>
        <p data-testid="carry">{data.carry.kind === "carry" && <><span className="pill good">Vay rẻ, gửi đắt</span> </>}{carryText(data.carry)}</p>
        <table className="fv-table" aria-label={`Thang thanh khoản ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Tiền và tương đương tiền</th><th className="num">Đầu tư tài chính ngắn hạn</th>
            <th className="num">Vay ngắn hạn</th><th className="num">Tiền + đầu tư NH / vay NH</th><th className="num">Trên tổng tài sản</th></tr></thead>
          <tbody>{data.liquidity.slice(-SHOWN).reverse().map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Tiền và tương đương tiền">{ty(r.cash)}</td>
              <td className="num" data-label="Đầu tư tài chính ngắn hạn">{ty(r.st_investments)}</td>
              <td className="num" data-label="Vay ngắn hạn">{ty(r.st_debt)}</td>
              <td className={`num${r.cover !== null && Number(r.cover) < 1 ? " negative" : ""}`} data-label="Tiền + đầu tư NH / vay NH">
                {r.cover === null ? "—" : `${Number(r.cover).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} lần`}</td>
              <td className="num" data-label="Trên tổng tài sản">{r.cash_share === null ? "—" : rate(r.cash_share)}</td>
            </tr>))}
          </tbody>
        </table>
        <p className="caption">Tiền và tương đương tiền gồm cả tiền gửi kỳ hạn đến 3 tháng; đầu tư tài chính ngắn hạn chủ yếu là tiền gửi 3–12 tháng (có thể có cả
          chứng khoán kinh doanh). Dưới 1 lần: tiền và đầu tư ngắn hạn chưa đủ trả vay ngắn hạn. Lợi suất trên tiền là ước tính thô: doanh thu tài chính còn gồm lãi
          tỷ giá, cổ tức và lãi bán khoản đầu tư; bình quân trên năm thời điểm cuối quý. “Vay rẻ, gửi đắt” khi nợ vay và tiền đều từ 5% tổng tài sản và chênh lệch
          dương, lợi suất trên tiền không quá 10%/năm và chi phí vay từ 2%/năm. Báo cáo công khai (VNDirect). Không phải khuyến nghị.</p>
      </section>
      <section className="surface" aria-label="Phải thu">
        <h2>Phải thu</h2>
        <p data-testid="dso">{dsoText(data.receivables.dso)}</p>
        <p data-testid="prepay-days">{prepayDaysText(data.receivables.prepay_days)}</p>
        {data.raise_prepay.events.map((e) => <p key={e.issue_date} data-testid="raise-prepay" className={e.flag ? "notice" : undefined}>
          {e.flag && <><span className="pill warn">Trả trước tăng sau huy động vốn</span> </>}{raiseText(e)}</p>)}
        <p data-testid="provision">{data.receivables.provision.kind === "jump" && <><span className="pill warn">Dự phòng tăng mạnh</span> </>}
          {provisionText(data.receivables.provision)}</p>
        <div className="tablewrap"><table className="fv-table" aria-label={`Phải thu ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Khách hàng</th><th className="num">Trả trước người bán</th><th className="num">Cho vay</th>
            <th className="num">Phải thu khác</th><th className="num">Dự phòng</th><th className="num">Tổng phải thu</th><th className="num">Trên tổng tài sản</th>
            <th className="num">Số ngày thu tiền</th><th className="num">Số ngày ứng trước</th></tr></thead>
          <tbody>{data.receivables.rows.slice(-SHOWN).reverse().map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Khách hàng">{ty(r.customers)}</td>
              <td className="num" data-label="Trả trước người bán">{ty(r.prepay)}</td>
              <td className="num" data-label="Cho vay">{ty(r.loans)}</td>
              <td className="num" data-label="Phải thu khác">{ty(r.other)}{r.other_share !== null && <span className="caption"> ({rate(r.other_share)} TS)</span>}</td>
              <td className="num" data-label="Dự phòng">{ty(r.provision)}</td>
              <td className="num" data-label="Tổng phải thu">{ty(r.total)}</td>
              <td className="num" data-label="Trên tổng tài sản">{r.total_share === null ? "—" : rate(r.total_share)}</td>
              <td className="num" data-label="Số ngày thu tiền">{r.dso === null ? "—" : `${r.dso} ngày`}</td>
              <td className="num" data-label="Số ngày ứng trước">{r.prepay_days === null ? "—" : `${r.prepay_days} ngày`}</td>
            </tr>))}
          </tbody>
        </table></div>
        <p className="caption">Mỗi cột cộng phần ngắn hạn và dài hạn (trả trước người bán: ngắn hạn); dự phòng mang dấu âm, đã trừ trong tổng. Số ngày thu tiền = phải
          thu khách hàng ngắn hạn cuối quý ÷ doanh thu bốn quý gần nhất × 365; trung vị ngành trên các mã theo dõi cùng ngành. Dự phòng được ghi là tăng mạnh khi
          tăng từ 50% so với cùng kỳ và bằng từ 1% phải thu ngắn hạn. Số ngày ứng trước = trả trước người bán cuối quý ÷ giá vốn bốn quý × 365: khoản này
          được thu hồi bằng hàng hóa, dịch vụ chứ không bằng tiền. Đợt huy động vốn (không tính cổ phiếu thưởng) được ghi nhận khi trả trước tăng từ một
          nửa số vốn điều lệ vừa thêm, trong quý ghi nhận vốn và quý kế tiếp. Phải thu từ bên liên quan và tên từng khách hàng chỉ có trong thuyết minh, không có ở đây.
          Từ năm 2026, Thông tư 99 bỏ chỉ tiêu phải thu về cho vay và gộp khoản cho vay vào phải thu khác: cột Cho vay về 0, cột Phải thu khác tăng
          tương ứng; khi so qua năm hãy cộng hai cột. Báo cáo công khai (VNDirect); ô thiếu số để trống. Không phải khuyến nghị.</p>
      </section>
      {data.property && <section className="surface" aria-label="Tiền khách trả trước">
        <h2>Tiền khách trả trước</h2>
        <p data-testid="advances-signal">{advancesText(data.property.signal)}</p>
        <table className="fv-table" aria-label={`Tiền khách trả trước ${symbol}`}>
          <thead><tr><th>Quý</th><th className="num">Khách trả trước</th><th className="num">Hàng tồn kho</th><th className="num">Dòng tiền kinh doanh</th><th className="num">LNST công ty mẹ</th></tr></thead>
          <tbody>{data.property.rows.slice(-SHOWN).reverse().map((r) => (
            <tr key={r.quarter}>
              <td data-label="Quý">{q(r.quarter)}</td>
              <td className="num" data-label="Khách trả trước">{ty(r.advances)}</td>
              <td className="num" data-label="Hàng tồn kho">{ty(r.inventory)}</td>
              <td className={`num${r.cfo !== null && Number(r.cfo) < 0 ? " negative" : ""}`} data-label="Dòng tiền kinh doanh">{ty(r.cfo)}</td>
              <td className={`num${r.npat_parent !== null && Number(r.npat_parent) < 0 ? " negative" : ""}`} data-label="LNST công ty mẹ">{ty(r.npat_parent)}</td>
            </tr>))}
          </tbody>
        </table>
        <p className="caption">Khách trả trước = người mua trả tiền trước ngắn hạn + dài hạn: tiền khách đã đóng cho căn chưa bàn giao. Khi bàn giao, khoản này giảm
          và chuyển thành doanh thu, lợi nhuận; vì vậy dòng tiền thường đi trước lợi nhuận. So với cùng quý năm trước. Không phải khuyến nghị.</p>
      </section>}
    </>
  );
}
