"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Fit = "driver" | "with" | "against" | "flat" | "none" | "missing";
type Mode = "tightening" | "easing" | null;
type Point = { date: string; value: string };
type Part = { id: string; direction: string | null; latest: Point; from: string; change: string; short_history: boolean; stale: boolean };
type Node = { id: string; direction: string | null; fit?: Fit; latest: Point | null; from?: string | null; change?: string | null;
  short_history?: boolean; stale: boolean; parts?: Part[]; core?: { date: string; value: string; change: string | null }; label?: string };
type Chain = { mode: Mode; driver: string | null; nodes: Pick<Node, "id" | "direction">[] | Node[]; with: string[]; against: string[];
  flat: string[]; missing: string[] };

const NAME: Record<string, string> = { us_cpi: "Lạm phát Mỹ (CPI)", us_rates: "Lãi suất Mỹ", dxy: "DXY", gold: "Vàng trong nước",
  usd_vnd: "Tỷ giá USD/VND (Vietcombank)" };
const SHORT: Record<string, string> = { us_cpi: "CPI Mỹ", us_rates: "lãi suất Mỹ", dxy: "DXY", gold: "vàng", usd_vnd: "tỷ giá USD/VND" };
const PART: Record<string, string> = { fed_effr: "Lãi suất Fed qua đêm (EFFR)", us10y: "Lợi suất trái phiếu Mỹ 10 năm" };
const MOVE: Record<string, string> = { up: "tăng", down: "giảm", flat: "đi ngang" };

const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const month = (iso: string) => `tháng ${Number(iso.slice(5, 7))}/${iso.slice(0, 4)}`;
const num = (v: string | number, digits = 2) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: digits });
const signed = (v: string | number, digits = 2) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${num(Math.abs(Number(v)), digits)}`;
const since = (from: string, short?: boolean) => short ? `chỉ có số từ ${day(from)}` : `so với ${day(from)}`;

/** One sentence: what set the chain's way this week, then the links with it, against it, flat, and without figures. */
export function chainSummary(c: Chain): string {
  if (!c.mode || !c.driver) return "Tuần này CPI Mỹ và lãi suất Mỹ đều đi ngang: chuỗi chưa có chiều rõ.";
  const driver = c.nodes.find((n) => n.id === c.driver);
  const head = `${SHORT[c.driver][0].toUpperCase()}${SHORT[c.driver].slice(1)} ${MOVE[driver?.direction ?? "flat"]} nên chuỗi đang theo chiều ${
    c.mode === "tightening" ? "thắt chặt" : "nới lỏng"}.`;
  const part = (label: string, ids: string[]) => ids.length ? ` ${label}: ${ids.map((i) => SHORT[i]).join(", ")}.` : "";
  return head + part("Khớp chuỗi", c.with) + part("Ngược chuỗi", c.against) + part("Đi ngang", c.flat) + part("Chưa có số", c.missing);
}

/** The pill text, its tone, and the node's class: tightening links in the "pressure" red, easing ones in the "support" green. */
export function fitLabel(fit: Fit, mode: Mode): [string, string, string] {
  const tone: [string, string] = mode === "easing" ? ["good", "chain-support"] : ["bad", "chain-pressure"];
  switch (fit) {
    case "driver": return ["mở đầu chuỗi", ...tone];
    case "with": return ["khớp chuỗi", ...tone];
    case "against": return ["ngược chuỗi", "warn", "chain-neutral"];
    case "missing": return ["chưa có số", "warn", "chain-missing"];
    case "flat": return ["đi ngang", "", "chain-neutral"];
    default: return ["chưa có chiều", "", "chain-neutral"];
  }
}

function Figure({ n }: { n: Node }) {
  if (n.fit === "missing") return <p className="muted">Chưa có số liệu.</p>;
  if (n.id === "us_cpi") return <>
    <p><strong>{num(n.latest!.value)}%</strong> <span className="caption">so cùng kỳ, {month(n.latest!.date)}
      {n.change != null ? ` (${signed(n.change)} điểm % so với ${month(n.from!)})` : ""}</span></p>
    {n.core && <p className="caption">CPI lõi: <strong>{num(n.core.value)}%</strong>, {month(n.core.date)}
      {n.core.change != null ? ` (${signed(n.core.change)} điểm % so với tháng trước)` : ""}</p>}</>;
  if (n.id === "us_rates") return <ul className="chain-parts">{n.parts!.map((p) => <li key={p.id}>{PART[p.id] ?? p.id} <strong>{num(p.latest.value)}%</strong>
    <span className="caption"> ({signed(p.change)} điểm % {since(p.from, p.short_history)})</span></li>)}</ul>;
  const unit = n.id === "gold" ? " đ/chỉ" : n.id === "usd_vnd" ? " đ" : "";
  return <><p><strong>{num(n.latest!.value, n.id === "dxy" ? 2 : 0)}{unit}</strong>
    <span className="caption"> ({signed(Number(n.change) * 100)}% {since(n.from!, n.short_history)})</span></p>
    {n.label && <p className="caption">{n.label}</p>}</>;
}

/** Chuỗi liên thị trường trong tuần: US CPI → US rates → DXY → gold → USD/VND, coloured by the week's real moves. */
export function UsChain() {
  const [c, setC] = useState<(Chain & { nodes: Node[] }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Chain & { nodes: Node[] }>("macro/us-chain").then(setC, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="Chuỗi liên thị trường trong tuần">
      <h2>Chuỗi liên thị trường trong tuần</h2>
      <p className="caption">Lạm phát Mỹ tăng làm kỳ vọng Fed giữ hoặc tăng lãi suất, lợi suất Mỹ và đồng USD (DXY) tăng; vàng, tài sản không sinh lãi,
        thường giảm; tỷ giá USD/VND chịu sức ép tăng. Chiều nới lỏng thì ngược lại. Mỗi ô so số mới nhất với khoảng một tuần trước (CPI: so tháng trước);
        ô khớp chuỗi tô theo chiều của chuỗi (đỏ: thắt chặt, xanh: nới lỏng). Chỉ mô tả dữ liệu, không phải khuyến nghị.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!c && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {c && <>
        <ol className="chain" aria-label="Các mắt xích, từ lạm phát Mỹ đến tỷ giá USD/VND">{c.nodes.map((n) => {
          const [word, tone, cls] = fitLabel(n.fit ?? "none", c.mode);
          return <li key={n.id} data-testid={`us-chain-${n.id}`} className={`chain-node ${cls}`}>
            <div className="chain-head"><strong>{NAME[n.id]}</strong><span className={`pill ${tone}`}>{word}</span></div>
            {n.direction && n.fit !== "missing" && <p className="chain-move">{MOVE[n.direction][0].toUpperCase() + MOVE[n.direction].slice(1)}</p>}
            <Figure n={n} />
            {n.stale && n.latest && <p className="caption">Số cũ: ngày {day(n.latest.date)}</p>}
          </li>;
        })}</ol>
        <p data-testid="us-chain-summary">{chainSummary(c)}</p>
      </>}
    </section>
  );
}
