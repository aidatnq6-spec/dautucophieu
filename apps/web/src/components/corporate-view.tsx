"use client";
import { useCallback, useEffect, useState } from "react";
import { BookPlus, EyeOff, RotateCcw } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatVnd } from "../lib/format";
import { TransactionForm, type LedgerEvent } from "./transaction-form";

type Suggestion = { id: string; symbol: string; kind: "cash" | "stock" | "rights"; title: string; exright: string; record: string | null;
  payout: string | null; value_per_share: number | null; ratio: number | null; eligible: number;
  status: "to_record" | "to_receive" | "waiting" | "to_credit" | "rights" | "upcoming"; draft: Record<string, unknown> | null };
type Costs = { year: number; sell_value: string; fees: string; sell_tax: string; dividends: string; dividend_tax: string; total: string };
type Data = { version: number; suggestions: Suggestion[]; costs: Costs[]; dismissed: { id: string; symbol: string; title: string; exright: string }[] };

const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const shares = (n: number) => n.toLocaleString("vi-VN");
const pct = (r: number | null) => (r === null ? "" : `${Number((r * 100).toFixed(2)).toLocaleString("vi-VN")}%`);
const NEEDS_ACTION = new Set(["to_record", "to_receive", "to_credit"]);

export function describeSuggestion(s: Omit<Suggestion, "draft"> & { draft: unknown }): string {
  const what = s.kind === "cash" ? `Cổ tức tiền ${(s.value_per_share ?? 0).toLocaleString("vi-VN")} đ/cp` : s.kind === "stock" ? `Cổ phiếu thưởng ${pct(s.ratio)}`
    : `Quyền mua ${pct(s.ratio)}`;
  const ex = `GDKHQ ${day(s.exright)}`;
  switch (s.status) {
    case "to_record": return `${what} · ${ex} · bạn có ${shares(s.eligible)} cp trước ngày này → ghi quyền vào sổ`;
    case "to_receive": return `${what} · trả ${s.payout ? day(s.payout) : "—"} → ghi tiền đã nhận`;
    case "waiting": return `${what} · đã ghi quyền, chờ trả ${s.payout ? day(s.payout) : "(nguồn chưa có ngày)"}`;
    case "to_credit": return `${what} · đã ghi quyền → ghi khi cổ phiếu về tài khoản`;
    case "rights": return `${what} · ${ex} · sổ chưa hỗ trợ quyền mua: nếu bạn thực hiện, ghi “Sự kiện chưa hỗ trợ”`;
    default: return `${what} · ${ex} · sắp tới, bạn đang có ${shares(s.eligible)} cp`;
  }
}

/** Cổ tức và quyền: ledger lines drafted from the Lịch sự kiện; the owner checks each against the broker's papers before saving. */
export function CorporateView({ ledgerVersion, events, onSaved }: { ledgerVersion: number; events: LedgerEvent[]; onSaved: () => void }) {
  const [data, setData] = useState<Data | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [open, setOpen] = useState<Suggestion | null>(null);
  const load = useCallback(() => api<Data>("ledger/corporate").then(setData, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải cổ tức.")), []);
  useEffect(() => { void load(); }, [load, ledgerVersion]);

  async function dismiss(action: "dismiss" | "restore", id: string) {
    if (!data) return;
    try {
      setData(await api<Data>("ledger/corporate", { method: "PUT", body: { action, id, expected_version: data.version, request_id: requestId() } }));
      setMessage(null);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu.");
    }
  }
  const draftEvent = (s: Suggestion): LedgerEvent => ({ event_id: "", sequence: 0, ...(s.draft as object) } as LedgerEvent);
  return (<>
    <section className="surface" aria-label="Cổ tức và quyền">
      <h2>Cổ tức và quyền</h2>
      <p className="caption">Soạn sẵn từ Lịch sự kiện cho mã bạn có trước ngày GDKHQ (theo sổ). Số dự kiến: cổ tức theo giá trị mỗi cổ phiếu của nguồn,
        thuế 5%; cổ phiếu thưởng làm tròn xuống. Hãy sửa theo chứng từ của công ty chứng khoán rồi mới ghi; chưa bấm ghi thì sổ không đổi.</p>
      {message && <p className="errors" role="alert">{message}</p>}
      {!data && !message && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {data && <>
        {data.suggestions.length === 0 && <p className="muted">Không có cổ tức hay quyền nào cần ghi.</p>}
        <ul className="co-list" aria-label="Gợi ý cổ tức và quyền">
          {data.suggestions.map((s) => <li key={s.id}>
            <div className="row"><strong>{s.symbol}</strong>
              <span className={`pill ${NEEDS_ACTION.has(s.status) ? "warn" : s.status === "rights" ? "bad" : ""}`}>{describeSuggestion(s)}</span>
              {s.draft && open?.id !== s.id && <button type="button" className="btn primary" onClick={() => setOpen(s)}>
                <BookPlus size={15} aria-hidden="true" />Ghi vào sổ</button>}
              {NEEDS_ACTION.has(s.status) && <button type="button" className="btn" aria-label={`Bỏ qua ${s.symbol} ${s.exright}`}
                onClick={() => { if (window.confirm("Bỏ qua gợi ý này? Có thể khôi phục ở dưới.")) void dismiss("dismiss", s.id); }}>
                <EyeOff size={15} aria-hidden="true" />Bỏ qua</button>}</div>
            {open?.id === s.id && <TransactionForm ledgerVersion={ledgerVersion} events={events} editing={null} draft={draftEvent(s)}
              onSaved={() => { setOpen(null); onSaved(); }} onCancel={() => setOpen(null)} />}
          </li>)}
        </ul>
        {data.dismissed.length > 0 && <details><summary className="caption">Đã bỏ qua ({data.dismissed.length})</summary>
          <ul className="co-list">{data.dismissed.map((d) => <li key={d.id}><span>{d.symbol} · {d.title} · GDKHQ {day(d.exright)}</span>
            <button type="button" className="btn" onClick={() => void dismiss("restore", d.id)}><RotateCcw size={15} aria-hidden="true" />Khôi phục</button></li>)}</ul>
        </details>}
      </>}
    </section>
    <section className="surface" aria-label="Thuế và phí theo năm">
      <h2>Thuế và phí theo năm</h2>
      {data && (data.costs.length === 0 ? <p className="muted">Sổ chưa có phí, thuế hay cổ tức đã nhận.</p> : <div className="tablewrap">
        <table aria-label="Thuế và phí theo năm">
          <thead><tr><th>Năm</th><th className="num">Giá trị bán</th><th className="num">Phí giao dịch</th><th className="num">Thuế bán</th>
            <th className="num">Cổ tức tiền đã nhận</th><th className="num">Thuế cổ tức</th><th className="num">Tổng thuế và phí</th></tr></thead>
          <tbody>{data.costs.map((c) => <tr key={c.year}><td>{c.year}</td><td className="num">{formatVnd(c.sell_value)}</td><td className="num">{formatVnd(c.fees)}</td>
            <td className="num">{formatVnd(c.sell_tax)}</td><td className="num">{formatVnd(c.dividends)}</td><td className="num">{formatVnd(c.dividend_tax)}</td>
            <td className="num"><strong>{formatVnd(c.total)}</strong></td></tr>)}</tbody>
        </table></div>)}
      <p className="caption">Chỉ những gì đã ghi trong sổ (phí và thuế theo chứng từ; cổ tức tiền gồm thực nhận và thuế khấu trừ). Không phải tư vấn thuế.</p>
    </section>
  </>);
}
