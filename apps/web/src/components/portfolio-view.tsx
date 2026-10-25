"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Undo2, XCircle } from "lucide-react";
import { ApiError, api, requestId, type ApiFailure } from "../lib/api";
import { formatVnd } from "../lib/format";
import { FormErrors } from "./form-errors";
import { LEDGER_ERRORS, TYPE_LABEL, TransactionForm, type LedgerEvent } from "./transaction-form";

type Holding = { security_id: string; quantity: number; pending_quantity: number; total_cost: string; average_cost: string; blocked_by: string[] };
type LedgerView = { version: number; events: LedgerEvent[]; original_events: LedgerEvent[]; audit: { amendment_id: string; action: string; target_event_id: string }[];
  state: { cash: string; realized_gain: string; dividend_income: string; dividend_receivable: string; net_contributions: string; positions: Holding[];
    realized_before_start_unknown: boolean }; stale: boolean };

function Signed({ value }: { value: string }) {
  const negative = value.startsWith("-");
  return <span className={negative ? "negative" : value === "0" ? "" : "positive"}>{negative ? "Lỗ " : value === "0" ? "" : "Lãi "}{formatVnd(value)}</span>;
}

const exists = (p: Promise<unknown>) => p.then(() => true, (e) => (e instanceof ApiError && e.failure.status === 404 ? false : Promise.reject(e)));
function fetchPortfolio() {
  return Promise.all([api<LedgerView>("ledger"), Promise.all([exists(api("profile")), exists(api("risk"))]).then(([profile, risk]) => ({ profile, risk }))]);
}

export function PortfolioView() {
  const [ledger, setLedger] = useState<LedgerView | null>(null);
  const [personal, setPersonal] = useState<{ profile: boolean; risk: boolean } | null>(null);
  const [editing, setEditing] = useState<LedgerEvent | null>(null);
  const [adding, setAdding] = useState(false);
  const [failure, setFailure] = useState<ApiFailure | null>(null);

  const load = useCallback(() => fetchPortfolio().then(([l, p]) => { setLedger(l); setPersonal(p); },
    (e) => { if (e instanceof ApiError) setFailure(e.failure); }), []);
  useEffect(() => { void load(); }, [load]);

  async function amend(action: "cancel" | "restore", target: string) {
    if (!ledger) return;
    const label = action === "cancel" ? "Hủy giao dịch này? Có thể khôi phục sau." : "Khôi phục giao dịch đã hủy?";
    if (!window.confirm(label)) return;
    try {
      await api("ledger/amendments", { method: "POST", body: { amendment: { amendment_id: `am-${requestId().slice(0, 20)}`, action, target_event_id: target,
        reason: action === "cancel" ? "Chủ sở hữu hủy" : "Chủ sở hữu khôi phục" }, expected_version: ledger.version, request_id: requestId() } });
      await load();
    } catch (e) { if (e instanceof ApiError) setFailure({ ...e.failure, message: LEDGER_ERRORS[e.failure.code] ?? e.failure.message }); }
  }

  if (!ledger) return <><FormErrors failure={failure} /><p className="muted">Đang tải sổ…</p></>;
  const active = new Set(ledger.events.map((e) => e.event_id));
  const cancelled = ledger.original_events.filter((e) => !active.has(e.event_id));
  const s = ledger.state;
  const saved = () => { setAdding(false); setEditing(null); void load(); };

  return (
    <>
      <FormErrors failure={failure} />
      {ledger.stale && <p className="notice">Đang xem bản sao cũ vì chưa kết nối được kho dữ liệu; không thể ghi giao dịch.</p>}
      {personal && (!personal.profile || !personal.risk) && (
        <p className="notice" data-testid="personalization-locked">
          Chưa đủ hồ sơ tài chính và khảo sát rủi ro, nên chưa mở phân bổ và khuyến nghị cá nhân hóa. <Link href="/onboarding">Hoàn tất thiết lập</Link>
        </p>
      )}
      <section className="surface">
        <div className="row"><h2>Tóm tắt sổ</h2><span className="caption">Phiên bản sổ {ledger.version}</span></div>
        <div className="formgrid">
          <div><div className="caption">Tiền trong sổ</div><strong data-testid="cash">{formatVnd(s.cash)}</strong></div>
          <div><div className="caption">Lãi/lỗ đã thực hiện</div><strong data-testid="realized"><Signed value={s.realized_gain} /></strong>
            {s.realized_before_start_unknown && <div className="caption">Chưa gồm lãi/lỗ trước ngày bắt đầu theo dõi</div>}</div>
          <div><div className="caption">Thu nhập cổ tức ròng</div><strong>{formatVnd(s.dividend_income)}</strong></div>
          <div><div className="caption">Cổ tức chờ nhận</div><strong>{formatVnd(s.dividend_receivable)}</strong></div>
          <div><div className="caption">Nộp ròng (không phải lợi nhuận)</div><strong>{formatVnd(s.net_contributions)}</strong></div>
        </div>
        <p className="caption">Lãi/lỗ chưa thực hiện cần giá thị trường đã xác minh; chưa có giá thì không tính bằng 0.</p>
      </section>

      <section className="surface">
        <h2>Cổ phiếu đang nắm giữ</h2>
        {s.positions.length === 0 ? <p className="muted">Chưa có cổ phiếu trong sổ.</p> : (
          <div className="tablewrap"><table aria-label="Cổ phiếu đang nắm giữ">
            <thead><tr><th>Mã</th><th className="num">Số lượng</th><th className="num">Chờ về</th><th className="num">Giá vốn bình quân (đ/cp)</th><th className="num">Tổng giá vốn</th><th>Ghi chú</th></tr></thead>
            <tbody>{s.positions.map((h) => (
              <tr key={h.security_id} data-testid={`holding-${h.security_id}`}>
                <td><strong>{h.security_id}</strong></td><td className="num">{h.quantity.toLocaleString("vi-VN")}</td>
                <td className="num">{h.pending_quantity.toLocaleString("vi-VN")}</td>
                <td className="num" data-testid={`avg-${h.security_id}`}>{formatVnd(h.average_cost, { unit: false })}</td>
                <td className="num">{formatVnd(h.total_cost)}</td>
                <td className="wrap">{h.blocked_by.length ? `Có sự kiện chưa hỗ trợ: ${h.blocked_by.join(", ")}` : ""}</td>
              </tr>))}</tbody>
          </table></div>
        )}
      </section>

      <section className="surface">
        <div className="row"><h2>Sổ giao dịch</h2>
          {!adding && !editing && <button className="btn primary" onClick={() => setAdding(true)} disabled={ledger.stale}><Plus size={16} aria-hidden="true" />Ghi nhận giao dịch</button>}</div>
        {(adding || editing) && <div className="surface"><TransactionForm key={editing?.event_id ?? "new"} ledgerVersion={ledger.version} events={ledger.events}
          editing={editing} onSaved={saved} onCancel={() => { setAdding(false); setEditing(null); }} /></div>}
        <div className="tablewrap"><table aria-label="Giao dịch">
          <thead><tr><th>Ngày</th><th className="num">Thứ tự</th><th>Loại</th><th>Mã</th><th className="num">Số lượng</th><th className="num">Giá / số tiền</th><th className="num">Phí / thuế</th><th>Thao tác</th></tr></thead>
          <tbody>
            {ledger.events.map((e) => (
              <tr key={e.event_id}>
                <td>{e.effective_at}</td><td className="num">{e.sequence}</td><td>{TYPE_LABEL[e.type] ?? e.type}</td><td>{e.security_id ?? ""}</td>
                <td className="num">{e.quantity?.toLocaleString("vi-VN") ?? ""}</td><td className="num">{formatVnd(e.price ?? e.amount ?? null)}</td>
                <td className="num">{e.fee !== undefined ? `${formatVnd(e.fee, { unit: false })} / ${formatVnd(e.tax ?? "0", { unit: false })}` : ""}</td>
                <td>{["buy", "sell", "deposit", "withdrawal"].includes(e.type) && <>
                  <button className="btn text" onClick={() => { setAdding(false); setEditing(e); }} aria-label={`Sửa giao dịch ${e.event_id}`}><Pencil size={15} aria-hidden="true" />Sửa</button>{" "}
                  <button className="btn text" onClick={() => void amend("cancel", e.event_id)} aria-label={`Hủy giao dịch ${e.event_id}`}><XCircle size={15} aria-hidden="true" />Hủy</button></>}</td>
              </tr>
            ))}
            {cancelled.map((e) => (
              <tr key={e.event_id} className="muted">
                <td>{e.effective_at}</td><td className="num">{e.sequence}</td><td>{TYPE_LABEL[e.type] ?? e.type} (đã hủy)</td><td>{e.security_id ?? ""}</td><td /><td /><td />
                <td><button className="btn text" onClick={() => void amend("restore", e.event_id)}><Undo2 size={15} aria-hidden="true" />Khôi phục</button></td>
              </tr>
            ))}
          </tbody>
        </table></div>
        {ledger.audit.length > 0 && <p className="caption">{ledger.audit.length} lần sửa/hủy/khôi phục được lưu vết.</p>}
      </section>
    </>
  );
}
