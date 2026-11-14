"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Passive = { goal: { target: string } | null; result: { required: string; income_now: string | null; progress: string | null; reached_on: string | null } | null };
type Contrib = { plan: { amount: string } | null; status: { planned: string; contributed: string; streak: number } | null };
type Layer = { id: string; share: string | null; target_min: string | null; target_max: string | null; status: string };
type Budget = { budget: { status?: string; pyramid?: { layers: Layer[] } | null } };
type Book = { liquidity: { now: string; reserve: string; status: "enough" | "short" } };
type Theses = { theses: { symbol: string; progress: { return: string; months: number; due: string; gain: string | null; reached: boolean; overdue: boolean } | null }[] };
export type Sources = { passive: Passive | null; contrib: Contrib | null; budget: Budget | null; book: Book | null; theses: Theses | null };
export type Row = { goal: string; actual: string; target: string; done: number | null; status: "ok" | "behind" | "over" | "unset"; href: string };

const LAYER: Record<string, string> = { deposit: "Tiền gửi (cùng tiền mặt)", bond: "Trái phiếu", gold: "Vàng", stocks: "Cổ phiếu", crypto: "Tiền số" };
const ratio = (a: string, b: string) => (Number(b) > 0 ? Number(a) / Number(b) : null);
const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** Thẻ điểm Mục tiêu – Thực tế: one row per goal the owner has set, from the pages that keep them; a goal not set says where to set it. */
export function scorecardRows(s: Sources): Row[] {
  const rows: Row[] = [];
  if (s.passive?.goal && s.passive.result) {
    const r = s.passive.result;
    rows.push({ goal: "Dòng tiền thụ động mỗi tháng", actual: r.income_now === null ? "chưa tính được" : formatVnd(r.income_now), target: formatVnd(s.passive.goal.target),
      done: r.progress === null ? null : Number(r.progress), status: r.progress !== null && Number(r.progress) >= 1 ? "ok" : "behind", href: "/profile?tab=dong-tien" });
  } else rows.push({ goal: "Dòng tiền thụ động mỗi tháng", actual: "—", target: "chưa đặt", done: null, status: "unset", href: "/profile?tab=dong-tien" });
  if (s.contrib?.plan && s.contrib.status) {
    const c = s.contrib.status, done = ratio(c.contributed, c.planned);
    rows.push({ goal: `Góp vốn đều (${formatVnd(s.contrib.plan.amount)}/tháng)`, actual: `${formatVnd(c.contributed)} · liên tục ${c.streak} tháng`,
      target: formatVnd(c.planned), done, status: done !== null && done >= 1 ? "ok" : "behind", href: "/profile?tab=ke-hoach" });
  } else rows.push({ goal: "Góp vốn đều", actual: "—", target: "chưa đặt", done: null, status: "unset", href: "/profile?tab=ke-hoach" });
  for (const l of s.budget?.budget.pyramid?.layers ?? []) {
    if (!LAYER[l.id] || l.target_min === null || l.target_max === null || l.share === null) continue;
    rows.push({ goal: `Tỷ trọng ${LAYER[l.id]}`, actual: formatRatio(l.share, 1), target: `${formatRatio(l.target_min, 0)}–${formatRatio(l.target_max, 0)}`,
      done: null, status: l.status === "ok" ? "ok" : l.status === "over" ? "over" : "behind", href: "/profile?tab=tai-san" });
  }
  if (s.book) {
    const q = s.book.liquidity;
    rows.push({ goal: "Quỹ dự phòng (tiền rút được ngay)", actual: formatVnd(q.now), target: formatVnd(q.reserve), done: ratio(q.now, q.reserve),
      status: q.status === "enough" ? "ok" : "behind", href: "/profile?tab=tai-san" });
  }
  for (const t of s.theses?.theses ?? []) {
    const p = t.progress;
    if (!p) continue;
    const gain = p.gain === null ? null : Number(p.gain) * 100;
    rows.push({ goal: `Luận điểm ${t.symbol}: +${p.return}% trong ${p.months} tháng`, actual: p.gain === null ? "chưa có giá" : `${gain! >= 0 ? "+" : ""}${formatRatio(p.gain, 1)}`,
      target: `+${p.return}% đến ${dmy(p.due)}`, done: gain === null ? null : gain / Number(p.return),
      status: p.reached ? "ok" : p.overdue ? "over" : "behind", href: "/portfolio" });
  }
  return rows;
}

const STATUS: Record<Row["status"], { text: string; cls: string }> = { ok: { text: "Đạt", cls: "good" }, behind: { text: "Chưa đạt", cls: "warn" },
  over: { text: "Vượt khung / quá hạn", cls: "bad" }, unset: { text: "Chưa đặt", cls: "" } };

async function maybe<T>(path: string): Promise<T | null> {
  try { return await api<T>(path); } catch { return null; }
}

export function GoalScorecard() {
  const [sources, setSources] = useState<Sources | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all([maybe<Passive>("passive-income"), maybe<Contrib>("contributions"), maybe<Budget>("equity-budget"), maybe<Book>("deposit-book"), maybe<Theses>("theses")])
      .then(([passive, contrib, budget, book, theses]) => { if (live) setSources({ passive, contrib, budget, book, theses }); });
    return () => { live = false; };
  }, []);
  const rows = sources ? scorecardRows(sources) : [];
  return (
    <section className="surface" aria-label="Thẻ điểm mục tiêu">
      <h2>Mục tiêu và thực tế</h2>
      {!sources ? <p className="muted fx-loading" role="status">Đang tải…</p> : <table className="fv-table" aria-label="Mục tiêu và thực tế">
        <thead><tr><th>Mục tiêu</th><th className="num">Thực tế</th><th className="num">Mục tiêu đặt</th><th className="num">Đạt</th><th>Trạng thái</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.goal}>
          <td data-label="Mục tiêu"><Link href={r.href}>{r.goal}</Link></td><td className="num" data-label="Thực tế">{r.actual}</td>
          <td className="num" data-label="Mục tiêu đặt">{r.target}</td>
          <td className="num" data-label="Đạt">{r.done === null ? "—" : formatRatio(String(Math.max(0, r.done)), 0)}</td>
          <td data-label="Trạng thái">{STATUS[r.status].cls ? <span className={`pill ${STATUS[r.status].cls}`}>{STATUS[r.status].text}</span> : STATUS[r.status].text}</td></tr>)}</tbody>
      </table>}
      <p className="caption">Gom các mục tiêu bạn đã đặt ở Hồ sơ &amp; rủi ro và Luận điểm; bấm tên mục tiêu để sửa. Số lấy từ đúng trang đó, không tính lại ở đây.</p>
    </section>
  );
}
