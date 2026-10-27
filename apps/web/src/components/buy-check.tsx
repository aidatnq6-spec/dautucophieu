"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio } from "../lib/format";

type Flag = { kind: "ticker" | "sector" | "stocks_layer" | "bottom_up" | "fomo"; symbol?: string; sector?: string; weight?: string; limit?: string;
  short?: string; over?: string[]; change?: string; from?: string };
type Check = { symbol: string; flags: Flag[]; basis: "equity_budget" | "investable_capital" | null };

const LAYER: Record<string, string> = { cash: "Tiền mặt", deposit: "Tiền gửi", bond: "Trái phiếu", gold: "Vàng", stocks: "Cổ phiếu", crypto: "Tiền số" };
const pct = (r: string) => formatRatio(r, 1).replace(",0%", "%");
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

function text(f: Flag, c: Check) {
  const capital = c.basis === "equity_budget" ? "vốn dành cho cổ phiếu" : "vốn có thể đầu tư";
  switch (f.kind) {
    case "ticker": return `${f.symbol} sẽ chiếm ${formatRatio(f.weight!, 1)} ${capital} (ngưỡng ${pct(f.limit!)}).`;
    case "sector": return `Ngành ${f.sector} sẽ chiếm ${formatRatio(f.weight!, 1)} ${capital} (ngưỡng ${pct(f.limit!)}).`;
    case "stocks_layer": return "Lớp Cổ phiếu trong tháp tài sản sẽ vượt mục tiêu theo khẩu vị rủi ro.";
    case "bottom_up": return `${LAYER[f.short!]} đang thiếu trong khi ${f.over!.map((o) => LAYER[o]).join(", ")} vượt mục tiêu: theo nguyên tắc tháp tài sản, lớp dưới nên được bổ sung trước.`;
    case "fomo": return `${c.symbol} đã tăng ${formatRatio(f.change!, 1)} từ ${day(f.from!)} (khoảng 3 tháng).`;
  }
}

/** Before a buy is saved: concentration and the asset pyramid after it, and a three-month run-up. A prompt to look again; never a block. */
export function BuyCheck({ symbol, amount }: { symbol: string; amount: number | null }) {
  const ready = /^[A-Z0-9]{3,10}$/.test(symbol) && amount !== null && amount > 0;
  const key = ready ? `${symbol}/${Math.round(amount!)}` : null;
  // Results are kept with the inputs they answer, so a stale answer is never shown for new inputs.
  const [result, setResult] = useState<{ key: string; check?: Check; error?: string } | null>(null);
  useEffect(() => {
    if (!key) return;
    const timer = window.setTimeout(() => {
      api<Check>(`buy-check/${key}`).then((check) => setResult({ key, check }),
        (e) => setResult({ key, error: e instanceof ApiError ? e.failure.message : "Chưa kiểm tra được." }));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [key]);
  if (!key) return null;
  const check = result?.key === key ? result.check ?? null : null;
  const error = result?.key === key ? result.error ?? null : null;
  return (
    <section className={`buy-check ${check?.flags.length ? "warn" : "ok"}`} aria-label="Kiểm tra trước khi mua">
      <strong>Kiểm tra trước khi mua</strong>
      {error && <p className="caption">{error}</p>}
      {!check && !error && <p className="caption fx-loading">Đang kiểm tra…</p>}
      {check && (check.flags.length === 0 ? <p className="caption">Không có cảnh báo.</p> : <>
        <ul>{check.flags.map((f, i) => <li key={i}>{text(f, check)}</li>)}</ul>
        <p><strong>Đây là quyết định đầu tư theo kế hoạch, hay mua vì sợ lỡ cơ hội?</strong> Bạn vẫn ghi lệnh được; nên ghi lại lý do ở ô bên dưới để tự xem lại sau.</p>
      </>)}
    </section>
  );
}
