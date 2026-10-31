"use client";
import { useEffect, useState } from "react";
import { BellPlus } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal } from "../lib/format";

type Alert = { id: string; symbol: string; op: "above" | "below"; price: string; created_at: string; triggered_at: string | null; triggered_price: string | null };
type View = { version: number; alerts: Alert[]; telegram_ready: boolean };

const OP = { above: "≥", below: "≤" } as const;

/** What the owner types, Vietnamese style (56,3 or 1.800), as a plain decimal for the API; null when it is not a number. */
export function levelInput(raw: string): string | null {
  const text = raw.trim().replace(/\s/g, "").replace(/\./g, "").replace(",", ".");
  return /^\d+(\.\d+)?$/.test(text) && Number(text) > 0 ? text : null;
}

/** Cảnh báo giá: levels for the indices and watched tickers, sent once over Telegram when crossed during the session. */
export function PriceAlerts({ symbol, canAlert }: { symbol: string; canAlert: boolean }) {
  const [view, setView] = useState<View | null>(null);
  const [op, setOp] = useState<"above" | "below">("above");
  const [level, setLevel] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<View>("trend/alerts").then(setView, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải cảnh báo.")); }, []);

  async function change(body: Record<string, string>) {
    if (!view) return;
    try {
      setView(await api<View>("trend/alerts", { method: "PUT", body: { ...body, expected_version: view.version, request_id: requestId() } }));
      setMessage(null);
      return true;
    } catch (e) {
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu cảnh báo.");
      return false;
    }
  }
  const parsed = levelInput(level);
  return (
    <section className="tb-alerts" aria-label="Cảnh báo giá">
      <h3>Cảnh báo giá (Telegram)</h3>
      {view && !view.telegram_ready && <p className="notice">Chưa bật gửi Telegram theo lịch trong Cài đặt: cảnh báo được lưu nhưng chưa gửi.</p>}
      {canAlert ? <form className="tb-alert-form" onSubmit={(e) => { e.preventDefault(); if (parsed) void change({ action: "add", symbol, op, price: parsed }).then((ok) => { if (ok) setLevel(""); }); }}>
        <span>{symbol}</span>
        <select aria-label="Điều kiện" value={op} onChange={(e) => setOp(e.target.value as "above" | "below")}>
          <option value="above">≥</option><option value="below">≤</option>
        </select>
        <input aria-label={`Mức giá ${symbol}`} inputMode="decimal" placeholder="56,3" value={level} onChange={(e) => setLevel(e.target.value)} />
        <button className="btn" type="submit" disabled={!view || !parsed}><BellPlus size={15} aria-hidden="true" />Thêm</button>
        {level && <span className="caption" data-testid="alert-preview">{parsed ? `Mức: ${formatDecimal(parsed, 2)}` : "Chưa phải số"}</span>}
      </form> : <p className="caption">Cảnh báo giá có cho chỉ số và mã cổ phiếu, chưa có cho các biến vĩ mô.</p>}
      {message && <p className="errors" role="alert">{message}</p>}
      {view && view.alerts.length > 0 && <ul className="tb-alert-list" aria-label="Danh sách cảnh báo">
        {view.alerts.map((a) => (
          <li key={a.id}>
            <span><strong>{a.symbol}</strong> {OP[a.op]} {formatDecimal(a.price, 2)}</span>
            <span className={a.triggered_at ? "pill good" : "pill warn"}>{a.triggered_at
              ? `đã báo ${new Date(a.triggered_at).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })} ở ${formatDecimal(a.triggered_price, 2)}`
              : "đang chờ"}</span>
            {a.triggered_at && <button className="btn" type="button" onClick={() => void change({ action: "rearm", id: a.id })}>Bật lại</button>}
            <button className="btn" type="button" aria-label={`Xóa cảnh báo ${a.symbol} ${OP[a.op]} ${a.price}`} onClick={() => void change({ action: "remove", id: a.id })}>Xóa</button>
          </li>
        ))}
      </ul>}
      <p className="caption">Kiểm tra mỗi 5 phút trong phiên (9:00–15:00); mỗi cảnh báo báo một lần. Cổ phiếu tính bằng nghìn đồng, chỉ số bằng điểm.</p>
    </section>
  );
}
