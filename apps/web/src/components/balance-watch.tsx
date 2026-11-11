"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type DebtRow = { quarter: string; debt: string | null; cash: string | null; net_debt: string | null; net_cash: boolean | null; debt_to_equity: string | null };
type Flag = { kind: "fast_borrowing" | null; quarter: string | null; debt: string | null; debt_2y_ago: string | null; ratio: string | null };
type SectorDebt = { members: number; growth_2y: string | null; compared: number; top: string | null;
  quarters: { quarter: string; count: number; debt: string | null; net_debt: string | null; net_count: number }[] };
type CashRow = { quarter: string; advances: string | null; inventory: string | null; cfo: string | null; npat_parent: string | null };
type Signal = { kind: "handover" | "collecting" | null; quarter: string | null; advances_yoy: string | null; profit_yoy: string | null };
type Balance = { symbol: string; sector: string | null; debt: { rows: DebtRow[]; flag: Flag }; sector_debt: SectorDebt | null;
  property: { rows: CashRow[]; signal: Signal } | null };

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
