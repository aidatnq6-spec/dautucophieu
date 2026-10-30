"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio } from "../lib/format";

type Ref = { source: string; page: number | null };
type Item = { name: string; note: string | null; share: string | null; basis: string | null; refs: Ref[] };
type Stage = "input" | "middle" | "output";
type Status = "good" | "bad" | "neutral" | "unknown";
type Reading = { direction: "up" | "down" | "flat" | null; change: string | null; kind: "ratio" | "points" | "net" | null; from: string | null; date: string; value: string; stale: boolean };
type Factor = { id: string; label: string; stage: Stage; indicator: string | null; indicator_label: string | null; when_up: "good" | "bad";
  weight: "major" | "minor" | "small"; share: string | null; why: string; refs: Ref[]; status: Status; reading: Reading | null };
type Label = "tailwind" | "neutral" | "headwind" | "insufficient" | null;
type Chain = { id: string; name: string; icb: string; status: "draft" | "approved"; label: Label; score: Record<Status, string>;
  symbols: { symbol: string; held: boolean }[]; stages: Record<Stage, Item[]>; factors: Factor[] };
type Source = { title: string; publisher: string; date: string; url: string };
type Data = { as_of: string; chains: Chain[]; sources: Record<string, Source>; uncovered: string[] };

const LABEL: Record<Exclude<Label, null>, { text: string; tone: string }> = {
  tailwind: { text: "Thuận gió", tone: "good" }, neutral: { text: "Trung tính", tone: "" }, headwind: { text: "Ngược gió", tone: "bad" },
  insufficient: { text: "Chưa đủ dữ liệu", tone: "warn" },
};
const STATUS: Record<Status, string> = { good: "tốt", bad: "xấu", neutral: "trung tính", unknown: "chưa đánh giá được" };
const WEIGHT = { major: "chính", minor: "phụ", small: "nhỏ" };
const STAGES: [Stage, string][] = [["input", "Đầu vào"], ["middle", "Trung gian"], ["output", "Đầu ra"]];
const day = (iso: string) => iso.split("-").reverse().join("/");
const pct = (v: string) => `${Math.round(Number(v) * 100)}%`;

function share(s: string) {
  const [lo, hi] = s.split("-");
  return hi ? `${formatRatio(lo, 0).replace(",0", "")}–${formatRatio(hi, 0).replace(",0", "")}` : formatRatio(lo, 0).replace(",0", "");
}

function move(r: Reading) {
  if (r.direction === null || r.change === null) return "chưa đủ điểm số liệu";
  const size = r.change.replace("-", "");
  if (r.kind === "net") return `${r.direction === "up" ? "mua ròng" : r.direction === "down" ? "bán ròng" : "cân bằng"} ${formatDecimal(size, 0)} tỷ đồng (20 phiên)`;
  const word = r.direction === "up" ? "tăng" : r.direction === "down" ? "giảm" : "đi ngang";
  return `${word} ${r.kind === "ratio" ? formatRatio(size, 1) : `${formatDecimal(size, 2)} điểm`}`;
}

function Refs({ refs, sources }: { refs: Ref[]; sources: Record<string, Source> }) {
  return <span className="vc-src">{refs.map((r, i) => { const s = sources[r.source];
    return <span key={i}>{i > 0 && " · "}<a href={s.url} target="_blank" rel="noreferrer">{s.publisher}, {day(s.date)}{r.page ? `, tr. ${r.page}` : ""}</a></span>; })}</span>;
}

function Bar({ score }: { score: Chain["score"] }) {
  const parts: [Status, string][] = [["good", "var(--good)"], ["neutral", "#9aa8b5"], ["unknown", "#d5dce3"], ["bad", "var(--bad)"]];
  return (
    <>
      <div className="vc-bar" aria-hidden="true">{parts.map(([k, c]) => <span key={k} style={{ width: pct(score[k]), background: c }} />)}</div>
      <p className="caption">tốt {pct(score.good)} · xấu {pct(score.bad)} · trung tính {pct(score.neutral)} · chưa đánh giá được {pct(score.unknown)}</p>
    </>
  );
}

function Diagram({ chain, sources }: { chain: Chain; sources: Record<string, Source> }) {
  return (
    <section className="surface vc-open" aria-label={`Chuỗi giá trị ${chain.name}`}>
      <h3>{chain.name} <span className="caption">({chain.icb})</span></h3>
      {chain.status === "draft" && <p className="notice">Chưa duyệt: nội dung soạn từ tài liệu công khai, chờ chủ sở hữu đọc và duyệt.</p>}
      <ol className="vc-flow">{STAGES.map(([stage, title]) => (
        <li key={stage} className="vc-stage">
          <h4>{title}</h4>
          <ul>{chain.stages[stage].map((it, i) => (
            <li key={i}><strong>{it.name}</strong>{it.share && <> · {share(it.share)}{it.basis ? ` ${it.basis}` : ""}</>}
              {it.note && <div className="caption">{it.note}</div>}<Refs refs={it.refs} sources={sources} /></li>))}
          </ul>
          <ul className="vc-factors">{chain.factors.filter((f) => f.stage === stage).map((f) => (
            <li key={f.id} className={`vc-factor vc-${f.status}`}>
              <strong>{f.label}</strong>: <span className="vc-status">{STATUS[f.status]}</span> · mức {WEIGHT[f.weight]}{f.share ? ` (${share(f.share)})` : ""}
              <div className="caption">{f.reading ? <>{f.indicator_label}: {move(f.reading)} từ {f.reading.from ? day(f.reading.from) : "—"} đến {day(f.reading.date)}
                {f.reading.stale && " (số liệu cũ)"}</> : "Ứng dụng chưa có chuỗi số liệu cho yếu tố này."}
                {" "}Khi tăng thì {f.when_up === "good" ? "tốt" : "xấu"} cho ngành: {f.why}</div>
              <Refs refs={f.refs} sources={sources} /></li>))}
          </ul>
        </li>))}
      </ol>
      <p>Mã theo dõi: {chain.symbols.map((s, i) => <span key={s.symbol}>{i > 0 && ", "}<Link href={`/research/${s.symbol}`}>{s.held ? <strong>{s.symbol}</strong> : s.symbol}</Link>
        {s.held && " (đang nắm)"}</span>)}</p>
    </section>
  );
}

/** Chuỗi giá trị: one card per value chain with the weighted macro reading; a card opens its sourced diagram. */
export function ValueChains() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { api<Data>("market/value-chains").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const current = data.chains.find((c) => c.id === open);
  return (
    <section className="surface" aria-label="Chuỗi giá trị">
      <h2>Chuỗi giá trị</h2>
      <p className="caption">Đầu vào, trung gian, đầu ra của từng ngành theo tài liệu công khai, và vĩ mô khoảng một tháng qua đang tốt hay xấu cho ngành
        (yếu tố chính tính 3, phụ 2, nhỏ 1). Chỉ để mô tả, không phải khuyến nghị.</p>
      {data.chains.length === 0 && <p className="muted">Chưa có chuỗi giá trị nào.</p>}
      <div className="vc-cards">{data.chains.map((c) => (
        <button key={c.id} className="vc-card" aria-expanded={open === c.id} onClick={() => setOpen(open === c.id ? null : c.id)}>
          <span className="vc-card-head"><strong>{c.name}</strong>
            {c.label ? <span className={`pill ${LABEL[c.label].tone}`}>{LABEL[c.label].text}</span> : <span className="pill warn">Chưa duyệt</span>}</span>
          <Bar score={c.score} />
          <span className="caption">{c.symbols.map((s) => s.symbol).join(", ")}{c.symbols.some((s) => s.held) && " · có mã đang nắm"}</span>
        </button>))}
      </div>
      {current && <Diagram chain={current} sources={data.sources} />}
      {data.uncovered.length > 0 && <p className="caption">Chưa có chuỗi giá trị cho: {data.uncovered.join(", ")}.</p>}
    </section>
  );
}
