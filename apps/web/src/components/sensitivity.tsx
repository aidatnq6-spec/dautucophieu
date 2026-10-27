"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio } from "../lib/format";

type Reading = { beta: string; t: string; class: "benefit" | "hurt" | "unclear" };
type Row = { symbol: string; held: boolean; status: "ok" | "insufficient"; weeks: number; oil?: Reading; usd?: Reading };
type Exposure = { total: string; oil: { benefit: string; hurt: string }; usd: { benefit: string; hurt: string }; insufficient: string };
type View = { factors: { oil: string | null; usd: string | null }; rows: Row[]; exposure: Exposure | null };

const pct = (r: string) => formatRatio(r, 1).replace(",0%", "%");
const CLASS: Record<string, [string, string]> = { benefit: ["hưởng lợi", "good"], hurt: ["chịu thiệt", "bad"], unclear: ["không rõ", ""] };
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** Extra weekly move beyond the VN-Index for a given factor move: oil +10%, the dollar index +1%. */
function Cell({ r, step }: { r: Reading; step: number }) {
  const move = Number(r.beta) * step;
  const [word, tone] = CLASS[r.class];
  return <>{`${move > 0 ? "+" : move < 0 ? "−" : ""}${Math.abs(move * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`}{" "}
    <span className={`pill ${tone}`}>{word}</span></>;
}

function Table({ rows, label }: { rows: Row[]; label: string }) {
  return (
    <table className="fv-table cc-table" aria-label={label}>
      <thead><tr><th>Mã</th><th className="num">Khi dầu tăng 10%</th><th className="num">Khi USD mạnh lên 1%</th><th className="num">Số tuần</th></tr></thead>
      <tbody>{rows.map((r) => <tr key={r.symbol}>
        <td data-label="Mã"><strong>{r.symbol}</strong>{r.held && <span className="pill"> đang nắm</span>}</td>
        {r.status === "ok" ? <>
          <td data-label="Khi dầu tăng 10%" className="num"><Cell r={r.oil!} step={0.1} /></td>
          <td data-label="Khi USD mạnh lên 1%" className="num"><Cell r={r.usd!} step={0.01} /></td>
        </> : <td colSpan={2} data-label="Độ nhạy" className="muted">chưa đủ dữ liệu (cần ít nhất 52 tuần)</td>}
        <td data-label="Số tuần" className="num">{r.weeks}</td></tr>)}</tbody>
    </table>
  );
}

/** How each held or watched ticker moved with oil and the US dollar beyond the market, over three years of weekly closes. */
export function Sensitivity() {
  const [v, setV] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<View>("macro/sensitivity").then(setV, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const clear = (r: Row) => r.held || (r.status === "ok" && (r.oil!.class !== "unclear" || r.usd!.class !== "unclear"));
  const shown = v?.rows.filter(clear) ?? [];
  const rest = v?.rows.filter((r) => !clear(r)) ?? [];
  const e = v?.exposure;
  return (
    <section className="surface" aria-label="Độ nhạy với giá dầu và đồng USD">
      <h2>Độ nhạy với giá dầu và đồng USD</h2>
      <p className="caption">Đo trên giá đóng cửa theo tuần trong khoảng 3 năm: khi dầu (WTI) hoặc đồng USD biến động, giá mã thường đi thêm bao nhiêu so với
        VN-Index. “Hưởng lợi”/“chịu thiệt” chỉ khi quan hệ đủ rõ để khó là ngẫu nhiên; còn lại là “không rõ”. Đồng USD đo bằng chỉ số USD rộng của Fed
        (so với rổ tiền tệ), không phải tỷ giá VND. Quan hệ trong quá khứ, không bảo đảm lặp lại; không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!v && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {v && <>
        {(!v.factors.oil || !v.factors.usd) && <p className="notice">Chưa có lịch sử giá dầu hoặc chỉ số USD; số sẽ có sau lượt đồng bộ vĩ mô kế tiếp.</p>}
        {e && <ul className="perf-bench" data-testid="sensitivity-exposure">
          {e.insufficient !== "1" && <><li>Vốn cổ phiếu đang nắm (theo giá mua): <strong>{pct(e.oil.benefit)}</strong> ở mã hưởng lợi khi dầu tăng, <strong>{pct(e.oil.hurt)}</strong> ở mã chịu thiệt.</li>
          <li>Khi USD mạnh lên: <strong>{pct(e.usd.benefit)}</strong> ở mã hưởng lợi, <strong>{pct(e.usd.hurt)}</strong> ở mã chịu thiệt.</li></>}
          {e.insufficient !== "0" && <li className="caption">{pct(e.insufficient)} vốn ở mã chưa đủ dữ liệu để đo.</li>}
        </ul>}
        {shown.length > 0 && <Table rows={shown} label="Mã đang nắm và mã có quan hệ rõ" />}
        {rest.length > 0 && <details className="dd-watch">
          <summary>{rest.length} mã chưa thấy quan hệ rõ hoặc chưa đủ dữ liệu</summary>
          <Table rows={rest} label="Các mã còn lại" />
        </details>}
        {v.factors.oil && <p className="caption">Giá dầu đến {day(v.factors.oil)}{v.factors.usd ? `, chỉ số USD đến ${day(v.factors.usd)}` : ""} (FRED).</p>}
      </>}
    </section>
  );
}
