"use client";
import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";

type Ticker = { symbol: string; sector: string; value: string | null; weight: string | null; over: boolean };
type Sector = { sector: string; value: string; weight: string; over: boolean; symbols: string[] };
type View = { status: "ok" | "no_capital"; basis?: "equity_budget" | "investable_capital"; limit: string; capital: string | null; tickers: Ticker[]; sectors: Sector[];
  cash: { value: string; weight: string } | null; missing_prices: string[]; what_if?: { symbol: string; amount: string } };

const pct = (v: string) => `${(Number(v) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;

function Bar({ weight, limit, over }: { weight: string; limit: string; over: boolean }) {
  const w = Math.max(0, Math.min(100, Number(weight) * 100));
  return (
    <span className="cc-bar" aria-hidden="true">
      <span className={`cc-fill${over ? " over" : ""}`} style={{ width: `${w}%` }} />
      <span className="cc-limit" style={{ left: `${Number(limit) * 100}%` }} />
    </span>
  );
}

/** With one ticker per sector the sector table repeats the ticker table; show it only when some sector groups several tickers. */
export function sectorsAddInformation(sectors: { symbols: string[] }[]): boolean {
  return sectors.some((s) => s.symbols.length > 1);
}

/** Weights of held tickers and sectors on investable capital, flagged above the owner's limit; what-if is not recorded. */
export function ConcentrationView() {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [symbol, setSymbol] = useState("");
  const [amount, setAmount] = useState("");
  const load = useCallback((query = "") => api<View>(`concentration${query}`).then((v) => { setView(v); setError(null); },
    (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")), []);
  useEffect(() => { void load(); }, [load]);
  const tryIt = (e: FormEvent) => {
    e.preventDefault();
    const clean = amount.replace(/[.\s]/g, "").replace(",", ".");
    if (!symbol.trim() || !clean || Number.isNaN(Number(clean))) { setError("Nhập mã và số tiền (đồng)."); return; }
    void load(`/whatif/${encodeURIComponent(symbol.trim())}/${encodeURIComponent(clean)}`);
  };
  const limitText = view ? pct(view.limit) : "";
  return (
    <section className="surface" aria-label="Phân bổ và rủi ro tập trung">
      <h2>Phân bổ và rủi ro tập trung</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!view ? <p className="muted fx-loading" role="status">Đang tải…</p> : view.status === "no_capital" ? (
        <p className="muted">Chưa có vốn có thể đầu tư trong hồ sơ tài chính, nên chưa tính được tỷ trọng.</p>
      ) : <>
        <p className="caption">Tỷ trọng trên {view.basis === "equity_budget" ? "vốn dành cho cổ phiếu" : "vốn có thể đầu tư"} ({formatVnd(view.capital)}), ngưỡng {limitText} cho một mã hoặc một ngành (sửa trong Cài đặt).
          Chỉ để theo dõi, không phải khuyến nghị.</p>
        {view.basis !== "equity_budget" && <p className="caption">Chưa nhập tổng tài sản tài chính: <Link href="/profile">nhập ở Hồ sơ & rủi ro</Link> để tính
          trên vốn dành cho cổ phiếu theo khẩu vị rủi ro.</p>}
        {view.what_if && <p className="notice">Chỉ là thử: {Number(view.what_if.amount) >= 0 ? "mua thêm" : "bán bớt"} {view.what_if.symbol}{" "}
          {formatVnd(String(Math.abs(Number(view.what_if.amount))))}; không ghi vào sổ. <button className="btn" type="button" onClick={() => void load()}>Bỏ thử</button></p>}
        <table className="fv-table cc-table" aria-label="Tỷ trọng theo mã">
          <thead><tr><th>Mã</th><th>Ngành</th><th className="num">Giá trị</th><th>Tỷ trọng</th></tr></thead>
          <tbody>{view.tickers.map((t) => <tr key={t.symbol} className={t.over ? "cc-over" : ""}>
            <td data-label="Mã"><strong>{t.symbol}</strong></td>
            <td data-label="Ngành">{t.sector}</td>
            <td data-label="Giá trị" className="num">{t.value ? formatVnd(t.value) : "Chưa có giá"}</td>
            <td data-label="Tỷ trọng">{t.weight ? <><Bar weight={t.weight} limit={view.limit} over={t.over} /> {pct(t.weight)}
              {t.over && <span className="pill bad"> vượt {limitText}</span>}</> : "—"}</td>
          </tr>)}
          {view.cash && <tr><td data-label="Mã"><strong>Còn trống</strong></td>
            <td data-label="Ngành">chưa dùng của {view.basis === "equity_budget" ? "vốn cho cổ phiếu" : "vốn có thể đầu tư"}</td>
            <td data-label="Giá trị" className="num">{formatVnd(view.cash.value)}</td><td data-label="Tỷ trọng">{pct(view.cash.weight)}</td></tr>}
          </tbody>
        </table>
        {!sectorsAddInformation(view.sectors) ? <p className="caption">Mỗi ngành chỉ có 1 mã nên tỷ trọng ngành bằng tỷ trọng mã.</p> :
        <table className="fv-table cc-table" aria-label="Tỷ trọng theo ngành">
          <thead><tr><th>Ngành</th><th>Mã</th><th className="num">Giá trị</th><th>Tỷ trọng</th></tr></thead>
          <tbody>{view.sectors.map((s) => <tr key={s.sector} className={s.over ? "cc-over" : ""}>
            <td data-label="Ngành"><strong>{s.sector}</strong></td>
            <td data-label="Mã">{s.symbols.join(", ")}</td>
            <td data-label="Giá trị" className="num">{formatVnd(s.value)}</td>
            <td data-label="Tỷ trọng"><Bar weight={s.weight} limit={view.limit} over={s.over} /> {pct(s.weight)}
              {s.over && <span className="pill bad"> vượt {limitText}</span>}</td>
          </tr>)}</tbody>
        </table>}
        {view.missing_prices.length > 0 && <p className="caption">Chưa có giá: {view.missing_prices.join(", ")} (chưa tính vào tỷ trọng).</p>}
        <form className="cc-try" onSubmit={tryIt}>
          <label className="field">Mã<input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} maxLength={10} /></label>
          <label className="field">Số tiền (đ, âm là bán)<input value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="numeric" /></label>
          <button className="btn" type="submit">Thử</button>
        </form>
      </>}
    </section>
  );
}
