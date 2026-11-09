"use client";
import { useState } from "react";
import { FileUp } from "lucide-react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";
import { toBase64 } from "./tcbs-import";

type Row = { year: number | null; orders: number; buys: number; sells: number; symbols: number; buy_value: string; sell_value: string; fee: string; tax: string; costs: string; cost_share: string | null;
  avg_hold_days: string | null; held_short: string | null; held_mid: string | null; held_long: string | null };
type View = { years: Row[]; total: Row | null; no_holding_time: string[]; duplicates: number; problems: { file: string; line: number; message: string }[] };

const MAX_BYTES = 700_000;
const MAX_TOTAL = 750_000;  // one request carries at most 1 MB, and base64 makes a file a third larger
const pct = (v: string | null, digits = 1) => (v === null ? "—" : formatRatio(v, digits));
const days = (v: string | null) => (v === null ? "—" : `${v.replace(".", ",")} ngày`);

function Line({ r, label }: { r: Row; label: string }) {
  return <tr><td data-label="Năm">{label}</td><td data-label="Số lệnh" className="num">{r.orders} <span className="caption">({r.buys} mua, {r.sells} bán)</span></td><td data-label="Số mã" className="num">{r.symbols}</td>
    <td data-label="Giá trị mua" className="num">{formatVnd(r.buy_value)}</td><td data-label="Giá trị bán" className="num">{formatVnd(r.sell_value)}</td><td data-label="Phí và thuế" className="num">{formatVnd(r.costs)}</td>
    <td data-label="Trên giá trị giao dịch" className="num">{pct(r.cost_share, 2)}</td><td data-label="Thời gian giữ" className="num">{days(r.avg_hold_days)}</td>
    <td data-label="Đến 30 ngày" className="num">{pct(r.held_short, 0)}</td><td data-label="31 đến 180 ngày" className="num">{pct(r.held_mid, 0)}</td><td data-label="Trên 180 ngày" className="num">{pct(r.held_long, 0)}</td></tr>;
}

/** Soi hành vi giao dịch: the TCBS files are read for this view only. Nothing is saved or added to Sổ giao dịch. */
export function TradeBehaviour() {
  const [view, setView] = useState<View | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function choose(list: FileList | null) {
    const files = [...(list ?? [])];
    if (!files.length) return;
    setView(null); setMessage(null);
    if (files.length > 12) { setMessage("Chọn tối đa 12 file."); return; }
    const big = files.find((f) => f.size > MAX_BYTES);
    if (big) { setMessage(`${big.name} quá lớn (tối đa khoảng 700 KB).`); return; }
    if (files.reduce((sum, f) => sum + f.size, 0) > MAX_TOTAL) { setMessage("Các file cộng lại quá lớn (tối đa khoảng 750 KB). Hãy chọn ít file hơn."); return; }
    setBusy(true);
    try {
      const body = { files: await Promise.all(files.map(async (f) => ({ name: f.name.slice(0, 120), content_base64: toBase64(new Uint8Array(await f.arrayBuffer())) }))) };
      setView(await api<View>("ledger/trade-behaviour", { method: "POST", body }));
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Không đọc được file."); } finally { setBusy(false); }
  }
  return (
    <details className="surface" aria-label="Soi hành vi giao dịch">
      <summary><strong>Soi hành vi giao dịch</strong></summary>
      <p className="caption">Chọn một hoặc nhiều file Lịch sử giao dịch cổ phiếu tải từ TCInvest. Phần mềm chỉ đọc để hiện bảng này: <strong>không lưu và không thêm gì vào sổ</strong>, tải lại trang là mất. Chỉ đưa số liệu, không đánh giá.</p>
      <div className="actions"><label className="btn"><FileUp size={16} aria-hidden="true" />{busy ? "Đang đọc…" : "Chọn file"}
        <input type="file" accept=".xlsx" multiple aria-label="Chọn các file sao kê TCBS" hidden disabled={busy} onChange={(e) => { void choose(e.target.files); e.target.value = ""; }} /></label></div>
      {message && <p className="errors" role="alert">{message}</p>}
      {view && (view.total === null ? <p className="muted">Không có lệnh hoàn tất nào trong các file này.</p> : <>
        <div className="tablewrap"><table aria-label="Hành vi giao dịch theo năm">
          <thead><tr><th>Năm</th><th className="num">Số lệnh</th><th className="num">Số mã</th><th className="num">Giá trị mua</th><th className="num">Giá trị bán</th><th className="num">Phí và thuế</th><th className="num">Trên giá trị giao dịch</th>
            <th className="num">Thời gian giữ</th><th className="num">Đến 30 ngày</th><th className="num">31 đến 180 ngày</th><th className="num">Trên 180 ngày</th></tr></thead>
          <tbody>{view.years.map((r) => <Line key={r.year} r={r} label={String(r.year)} />)}</tbody>
          <tfoot className="fv-median"><Line r={view.total} label="Tổng" /></tfoot>
        </table></div>
        <p className="caption">Thời gian giữ tính theo mua trước bán trước, bình quân theo số cổ phiếu, xếp vào năm bán. Ba cột cuối là tỷ lệ số cổ phiếu đã bán theo thời gian giữ.
          Cổ phiếu thưởng hay cổ tức bằng cổ phiếu không có trong file, nên thời gian giữ của mã có các sự kiện này chỉ gần đúng.</p>
        {view.no_holding_time.length > 0 && <p className="notice">Chưa tính thời gian giữ, vì bán nhiều hơn số đã mua trong file: {view.no_holding_time.join(", ")}. Số lệnh, giá trị và phí vẫn được tính.</p>}
        {view.duplicates > 0 && <p className="caption">Có {view.duplicates} dòng trùng giữa các file, chỉ tính một lần.</p>}
        {view.problems.length > 0 && <details><summary>{view.problems.length} dòng không tính</summary><ul className="ft-checks" aria-label="Dòng không tính">{view.problems.map((p) => <li key={`${p.file}-${p.line}`}>{p.file}, dòng {p.line}: {p.message}</li>)}</ul></details>}
      </>)}
    </details>
  );
}
