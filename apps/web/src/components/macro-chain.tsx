"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Part = { id: string; direction: string | null; latest: { date: string; value: string }; from: string; change: string; short_history: boolean; stale: boolean };
type Node = { id: string; direction: string | null; effect: "pressure" | "support" | "neutral" | "missing"; latest: { date: string; value: string } | null;
  from?: string | null; change?: string | null; short_history?: boolean; stale: boolean; sessions?: number; parts?: Part[] };
type Chain = { nodes: Node[]; pressure: string[]; support: string[]; missing: string[] };

const NAME: Record<string, string> = { oil: "Giá dầu (WTI)", inflation: "Lạm phát Việt Nam", rates: "Lãi suất Việt Nam", foreign: "Khối ngoại", vnindex: "VN-Index" };
const SHORT: Record<string, string> = { oil: "giá dầu", inflation: "lạm phát", rates: "lãi suất", foreign: "khối ngoại", vnindex: "VN-Index" };
const RATE_NAME: Record<string, string> = { vn_interbank_on: "Liên ngân hàng qua đêm", vn10y: "TPCP 10 năm" };
const MOVE: Record<string, string> = { up: "Tăng", down: "Giảm", flat: "Đi ngang", buy: "Mua ròng", sell: "Bán ròng" };
const EFFECT: Record<string, [string, string]> = { pressure: ["tạo áp lực", "bad"], support: ["hỗ trợ", "good"], neutral: ["trung tính", ""],
  missing: ["chưa có số", "warn"] };

const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const num = (v: string | number, digits = 2) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: digits });
const signed = (v: string, digits = 2) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${num(Math.abs(Number(v)), digits)}`;
const since = (from: string, short?: boolean) => short ? `chỉ có số từ ${day(from)}` : `so với ${day(from)}`;

function Figure({ n }: { n: Node }) {
  if (n.effect === "missing") return <p className="muted">Chưa có số liệu{n.id === "inflation" ? " — nhập tay ở bảng bên dưới" : ""}.</p>;
  const l = n.latest;
  switch (n.id) {
    case "oil": case "vnindex":
      return <p><strong>{num(l!.value)}{n.id === "oil" ? " USD/thùng" : " điểm"}</strong>
        <span className="caption"> ({signed(String(Number(n.change) * 100), 1)}% {since(n.from!, n.short_history)})</span></p>;
    case "inflation":
      return <p><strong>{num(l!.value)}%</strong> <span className="caption">so cùng kỳ, tháng {l!.date.slice(5, 7)}/{l!.date.slice(0, 4)}
        {n.change !== null && n.change !== undefined ? ` (${signed(n.change)} điểm % so với tháng trước)` : ""}</span></p>;
    case "foreign":
      return <p><strong>{n.direction === "sell" ? "Bán" : "Mua"} ròng {num(Math.abs(Number(l!.value)), 0)} tỷ đ</strong>
        <span className="caption"> ({n.sessions} phiên từ {day(n.from!)})</span></p>;
    default:
      return <ul className="chain-parts">{n.parts!.map((p) => <li key={p.id}>{RATE_NAME[p.id] ?? p.id} <strong>{num(p.latest.value)}%</strong>
        <span className="caption"> ({signed(p.change)} điểm % {since(p.from, p.short_history)})</span></li>)}</ul>;
  }
}

/** Oil → inflation → rates → foreign flows → VN-Index: each link's direction over about a month and whether it weighs on stocks. */
export function MacroChain() {
  const [c, setC] = useState<Chain | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Chain>("macro/chain").then(setC, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const list = (ids: string[]) => ids.map((i) => SHORT[i]).join(", ");
  return (
    <section className="surface" aria-label="Chuỗi tác động vĩ mô">
      <h2>Chuỗi tác động vĩ mô</h2>
      <p className="caption">Giá dầu đẩy lạm phát, lạm phát kéo lãi suất, lãi suất ảnh hưởng dòng vốn ngoại, rồi đến VN-Index. Mỗi ô so số mới nhất với khoảng
        1 tháng trước; đỏ là đang tạo áp lực lên cổ phiếu, xanh là đang hỗ trợ. Chỉ mô tả dữ liệu, không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!c && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {c && <>
        <ol className="chain" aria-label="Các mắt xích, từ giá dầu đến VN-Index">
          {c.nodes.map((n) => {
            const [word, tone] = EFFECT[n.effect];
            return (
              <li key={n.id} data-testid={`chain-${n.id}`} className={`chain-node chain-${n.effect}`}>
                <div className="chain-head"><strong>{NAME[n.id]}</strong><span className={`pill ${tone}`}>{word}</span></div>
                {n.direction && n.effect !== "missing" && <p className="chain-move">{MOVE[n.direction]}</p>}
                <Figure n={n} />
                {n.stale && n.latest && <p className="caption">Số cũ: ngày {day(n.latest.date)}</p>}
              </li>
            );
          })}
        </ol>
        <p data-testid="chain-summary">
          {c.pressure.length > 0 && <><strong>Đang tạo áp lực:</strong> {list(c.pressure)}. </>}
          {c.support.length > 0 && <><strong>Đang hỗ trợ:</strong> {list(c.support)}. </>}
          {c.missing.length > 0 && <><strong>Chưa có số:</strong> {list(c.missing)}.</>}
          {c.pressure.length + c.support.length + c.missing.length === 0 && "Các mắt xích đều đi ngang."}
        </p>
      </>}
    </section>
  );
}
