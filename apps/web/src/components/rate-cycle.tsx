"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Reading = { id: string; direction: "up" | "down" | "flat"; change: string; from: string; latest: string };
type Cycle = { basis: "vietnam" | "us_reference" | null; phase: "up" | "down" | "flat" | null; series: Reading[];
  vietnam_since: string | null; vietnam_ready_on: string | null };

const NAME: Record<string, string> = { deposit_12m: "Lãi tiền gửi 12 tháng", vn10y: "Lợi suất TPCP Việt Nam 10 năm", fed_effr: "Lãi suất Fed",
  us10y: "Lợi suất trái phiếu Mỹ 10 năm" };
const PHASE: Record<string, string> = { up: "đang tăng", down: "đang giảm", flat: "đi ngang" };
// What usually leads in each phase, in VWA's cycle logic (GDP, inflation → rates → asset classes). A description, not advice.
const LEADS: Record<string, string> = {
  up: "Khi lãi suất tăng, tiền gửi và tài sản thu nhập cố định thường hấp dẫn hơn; cổ phiếu và bất động sản thường chịu áp lực định giá.",
  down: "Khi lãi suất giảm, cổ phiếu và bất động sản thường được hưởng lợi; lãi tiền gửi kém hấp dẫn dần.",
  flat: "Khi lãi suất đi ngang, không lớp tài sản nào được ưu tiên rõ rệt chỉ vì lãi suất.",
};
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const num = (v: string) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 2 });

/** Six-month direction of rates: Vietnam's once six months are stored, the US as a labelled reference until then. */
export function RateCycle() {
  const [c, setC] = useState<Cycle | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Cycle>("macro/cycle").then(setC, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Mốc chu kỳ lãi suất">
      <h2>Mốc chu kỳ lãi suất</h2>
      {error && <p className="errors" role="alert">{error}</p>}
      {!c && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {c && <>
        {c.basis !== "vietnam" && <p className="notice">Lãi suất Việt Nam: chưa đủ 6 tháng dữ liệu Việt Nam
          {c.vietnam_since ? ` (lưu từ ${day(c.vietnam_since)}, đủ vào khoảng ${day(c.vietnam_ready_on!)})` : ""}.
          {c.basis === "us_reference" ? " Tạm dùng lãi suất Mỹ làm tham chiếu." : ""}</p>}
        {c.phase ? <>
          <p><strong>{c.basis === "us_reference" ? "Tham chiếu Mỹ: lãi suất" : "Lãi suất Việt Nam"} {PHASE[c.phase]}</strong> trong khoảng 6 tháng qua.</p>
          <ul className="perf-bench">{c.series.map((s) => <li key={s.id}>{NAME[s.id] ?? s.id}: {num(s.latest)}% ({Number(s.change) > 0 ? "+" : ""}{num(s.change)} điểm %
            so với {day(s.from)})</li>)}</ul>
          <p className="caption">{LEADS[c.phase]} Đây là logic chu kỳ chung (GDP, lạm phát → lãi suất → lớp tài sản), không phải khuyến nghị.</p>
        </> : <p className="muted">Chưa đủ dữ liệu để đọc xu hướng; không phải khuyến nghị.</p>}
      </>}
    </section>
  );
}
