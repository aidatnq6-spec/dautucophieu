"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";
import { gapText, type Catalyst, type Question, QUESTIONS } from "./thesis-questions";
import { type Bands, ValuationBands } from "./valuation-bands";

type Grade = "good" | "watch" | "bad";
type View = { symbol: string; close: string | null; close_date: string | null; updated_on: string | null; stage: "draft" | "reviewed";
  model: { headline: string; summary: string; questions: Record<string, Question>; review: { when: string; on: string | null } };
  scenarios: { rows: { name: "bad" | "base" | "good"; price: string; prob: string; note: string; upside: string | null }[]; expected: string | null; upside: string | null } | null;
  indicators: { id: string; name: string; tier: string; unit: string; bad: string; base: string; good: string; current: string | null; period: string | null; grade: Grade | null }[];
  lights: Record<Grade | "none", number>; questions: Record<string, Question>; gaps: { open: number; total: number }; catalysts: Catalyst[]; bands: Bands;
  auto_catalysts: Catalyst[]; facts: Record<string, string[]>; auto_gaps: Record<string, string[]> };

const SCEN = { bad: "Xấu", base: "Cơ sở", good: "Tốt" };
const TIER: Record<string, string> = { lead: "Dẫn", coincident: "Đồng hành", lag: "Sau", valuation: "Định giá" };
const GRADE: Record<Grade, [string, string]> = { good: ["Tốt", "good"], watch: ["Theo dõi", "warn"], bad: ["Xấu", "bad"] };
const dmy = (iso: string | null) => (iso ? iso.split("-").reverse().join("/") : "");
const signed = (v: string | null) => (v === null ? "—" : `${Number(v) > 0 ? "+" : ""}${formatRatio(v, 1)}`);

/** Trang luận điểm 1 trang: everything kept for one ticker's thesis on one A4 page, to read or print. */
export function ThesisOnePager({ symbol }: { symbol: string }) {
  const [v, setV] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<View>(`stock/${encodeURIComponent(symbol)}/model`).then(setV, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, [symbol]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!v) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const s = v.scenarios;
  return (
    <div className="op-page">
      <div className="op-tools"><Link href={`/research/${v.symbol}`}>← Trang {v.symbol}</Link>
        <button type="button" className="btn" onClick={() => window.print()}>In</button></div>
      <header className="op-head surface">
        <h1>{v.model.headline || `Luận điểm ${v.symbol}`}</h1>
        {v.model.summary && <p>{v.model.summary}</p>}
        <p className="caption"><span className={`pill ${v.stage === "reviewed" ? "good" : "warn"}`}>{v.stage === "reviewed" ? "Đã nghiệm thu" : "Nháp"}</span>
          {" "}{v.symbol}{v.updated_on ? ` · cập nhật ${dmy(v.updated_on)}` : ""}</p>
      </header>
      <div className="op-tiles">
        <div><span>Giá {v.close_date ? dmy(v.close_date).slice(0, 5) : ""}</span><strong>{formatVnd(v.close)}</strong></div>
        <div><span>Giá kỳ vọng (3 kịch bản)</span><strong>{s?.expected ? formatVnd(s.expected) : "—"}</strong></div>
        <div><span>Tiềm năng so giá hiện tại</span><strong className={s?.upside && Number(s.upside) >= 0 ? "fd-up" : "fd-down"}>{signed(s?.upside ?? null)}</strong></div>
        <div><span>Đèn theo dõi</span><strong>{v.lights.good} tốt{v.lights.bad ? ` · ${v.lights.bad} xấu` : ""}</strong></div>
        <div><span>Độ đủ dữ liệu</span><strong>{gapText(v.questions, v.auto_gaps)}</strong></div>
      </div>
      <div className="op-two">
        <section className="surface" aria-label="Dải định giá"><h2>Định giá: khoảng theo từng cách (đ/CP)</h2><ValuationBands bands={v.bands} compact /></section>
        <section className="surface" aria-label="Ba kịch bản"><h2>Ba kịch bản</h2>
          {s && s.rows.length ? <table className="op-table"><tbody>{s.rows.map((r) => <tr key={r.name}>
            <th>{SCEN[r.name]} · {r.prob}%</th><td className="num"><strong>{formatVnd(r.price)}</strong><div className="caption">{signed(r.upside)}</div></td><td>{r.note}</td></tr>)}</tbody></table>
            : <p className="muted">Chưa nhập kịch bản.</p>}
          {v.model.review.when && <p className="notice">Xem lại khi: {v.model.review.when}{v.model.review.on ? ` (${dmy(v.model.review.on)})` : ""}.</p>}
        </section>
      </div>
      <div className="op-questions">{QUESTIONS.map(([key, title], n) => { const q = v.questions[key];
        return <section key={key} className="surface op-q" aria-label={`Câu ${n + 1}`}>
          <div className="row"><h3>{n + 1} · {title}</h3>{q?.status && <span className={`pill ${GRADE[q.status][1]}`}>{GRADE[q.status][0]}</span>}</div>
          {q?.summary ? <p className="op-sum">{q.summary}</p> : null}
          {q && q.points.length > 0 && <ul>{q.points.map((p, i) => <li key={i}>{p}</li>)}</ul>}
          {(v.facts[key] ?? []).length > 0 && <ul className="tq-facts">{v.facts[key].map((f) => <li key={f}>{f}</li>)}</ul>}
          {!q?.summary && !(v.facts[key] ?? []).length && <p className="muted">Chưa trả lời.</p>}
          {(v.auto_gaps[key] ?? []).map((g) => <p key={g} className="op-gap"><span className="pill warn">GAP</span> {g}</p>)}
          {q?.gaps.filter((g) => !g.done).map((g) => <p key={g.id} className="op-gap"><span className="pill warn">GAP</span> {g.text}{g.ref ? ` (${g.ref})` : ""}</p>)}
        </section>; })}</div>
      <div className="op-two">
        <section className="surface" aria-label="Chỉ báo theo dõi"><h2>Chỉ báo theo dõi</h2>
          {v.indicators.length ? <table className="op-table"><thead><tr><th>Chỉ báo</th><th>Tầng</th><th className="num">Hiện tại</th><th className="num">Xấu</th>
            <th className="num">Cơ sở</th><th className="num">Tốt</th><th>Đánh giá</th></tr></thead>
            <tbody>{v.indicators.map((i) => <tr key={i.id}><td>{i.name}{i.unit ? ` (${i.unit})` : ""}</td><td>{TIER[i.tier]}</td>
              <td className="num"><strong>{i.current === null ? "—" : formatDecimal(i.current, 1)}</strong></td><td className="num">{formatDecimal(i.bad, 1)}</td>
              <td className="num">{formatDecimal(i.base, 1)}</td><td className="num">{formatDecimal(i.good, 1)}</td>
              <td>{i.grade ? <span className={`pill ${GRADE[i.grade][1]}`}>{GRADE[i.grade][0]}</span> : "—"}</td></tr>)}</tbody></table>
            : <p className="muted">Chưa có chỉ báo.</p>}
          <p className="caption">Tốt = bằng hoặc vượt mức Cơ sở; Xấu = chạm mức Xấu; giữa = Theo dõi.</p>
        </section>
        <section className="surface" aria-label="Mốc và sự kiện"><h2>Mốc và sự kiện</h2>
          {v.catalysts.length + v.auto_catalysts.length ? <table className="op-table"><tbody>{[...v.catalysts, ...v.auto_catalysts].map((c) => <tr key={c.id} className={c.done ? "tq-done" : undefined}>
            <th>{c.when || "chưa có mốc"}</th><td className={c.sign === "+" ? "fd-up" : c.sign === "-" ? "fd-down" : undefined}><strong>{c.sign === "-" ? "−" : c.sign}</strong></td>
            <td>{c.text}{c.source && <span className="caption"> — {c.source}</span>}</td></tr>)}</tbody></table> : <p className="muted">Chưa có mốc.</p>}
        </section>
      </div>
      <p className="caption op-foot">Mô tả trạng thái, không phải khuyến nghị mua/bán. Giá và số tự động lấy từ dữ liệu công khai đã lưu; kịch bản, câu trả lời, ngưỡng và mốc là của bạn.</p>
    </div>
  );
}
