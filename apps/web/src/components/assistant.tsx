"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Bot, Send, X } from "lucide-react";
import { api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";
import { type Intent, parse } from "../lib/assistant";
import type { Glance } from "./overview-glance";

type Answer = { title: string; lines: string[]; links: { label: string; href: string }[] };
type Message = { from: "me" | "bot"; text?: string; answer?: Answer };

const QUICK: { label: string; ask: string }[] = [
  { label: "Hôm nay cần để ý gì", ask: "hôm nay có gì cần để ý" }, { label: "Danh mục hôm nay", ask: "lãi lỗ hôm nay" },
  { label: "Tiền sắp về", ask: "tiền sắp về, đáo hạn, cổ tức" }, { label: "Luận điểm cần xem lại", ask: "luận điểm" },
  { label: "Bản tin phiên gần nhất", ask: "bản tin" }, { label: "Hệ thống có lỗi không", ask: "hệ thống có lỗi không" },
];
const HELLO: Answer = { title: "Chào bạn, mình là trợ lý của Quản lý Gia Sản.", links: [],
  lines: ["Bấm một nút bên dưới, hoặc gõ: một mã (FPT, định giá HPG, cổ tức KDH), \"sổ nào sắp đáo hạn\", hay tên một trang (\"thác nước\", \"quỹ mở\").",
    "Mọi câu trả lời tính ngay trên máy bạn từ số liệu đã có; không gửi gì ra ngoài."] };
const dmy = (iso: string) => iso.slice(0, 10).split("-").reverse().join("/");
const signed = (v: string | null, digits = 1) => (v === null ? "—" : `${Number(v) > 0 ? "+" : ""}${formatRatio(v, digits)}`);
const money = (v: string) => `${Number(v) > 0 ? "+" : ""}${formatVnd(v)}`;

async function maybe<T>(path: string): Promise<T | null> {
  try { return await api<T>(path); } catch { return null; }
}

/** The answer card for an intent, from the same pages' data (nothing computed twice, nothing sent out). */
async function answer(intent: Intent): Promise<Answer> {
  switch (intent.kind) {
    case "today": {
      const g = await maybe<Glance>("glance");
      const items = g?.attention.items ?? [];
      return { title: "Hôm nay cần để ý", lines: items.length ? items.slice(0, 6).map((i) => `${i.level === "high" ? "● " : "○ "}${i.text}`)
        : ["Không có gì cần để ý ngay."], links: [...items.slice(0, 3).map((i) => ({ label: i.symbol ?? "Xem", href: i.href })), { label: "Tổng quan", href: "/" }] };
    }
    case "portfolio": {
      const [g, d] = await Promise.all([maybe<Glance>("glance"), maybe<{ days: { date: string; status: string; gain?: string; return?: string | null; tickers?: { symbol: string; amount: string }[] }[] }>("performance-daily")]);
      const k = g?.kpis, last = d?.days.filter((x) => x.status === "ok").at(-1);
      const lines = k ? [`Giá trị cổ phiếu: ${formatVnd(k.market_value)} (${k.held_count} mã), lãi/lỗ so với vốn ${money(k.unrealized_gain)}.`,
        k.day_change !== null ? `Phiên ${g!.session_date ? dmy(g!.session_date) : ""}: ${money(k.day_change)} (${signed(k.day_change_ratio, 2)}); VN-Index ${signed(k.vnindex_change_ratio, 2)}.`
          : "Chưa có hai phiên đóng cửa để so."] : ["Chưa đọc được danh mục."];
      if (last?.tickers?.length) lines.push(`Kéo nhiều nhất ngày ${dmy(last.date)}: ${last.tickers.map((t) => `${t.symbol} ${money(t.amount)}`).join(", ")}.`);
      return { title: "Danh mục hôm nay", lines, links: [{ label: "Danh mục & Giao dịch", href: "/portfolio" }, { label: "Tổng kết tháng", href: "/monthly" }] };
    }
    case "money_in": {
      const [book, ev] = await Promise.all([
        maybe<{ calendar: { months: { month: string; count: number; principal: string; interest: string }[]; due_soon: string[]; overdue: string[] }; liquidity: { maturing_90d: string } }>("deposit-book"),
        maybe<{ upcoming: { symbol: string; kind: string; title: string; key_date: string | null; payout: string | null; held: boolean }[] }>("events")]);
      const lines: string[] = [];
      if (book) {
        lines.push(`Sổ tiết kiệm đến hạn trong 90 ngày: ${formatVnd(book.liquidity.maturing_90d)}${book.calendar.overdue.length ? `; ${book.calendar.overdue.length} sổ đã quá hạn` : ""}.`);
        lines.push(...book.calendar.months.slice(0, 3).map((m) => `Tháng ${m.month.slice(5)}/${m.month.slice(0, 4)}: ${m.count} sổ, gốc ${formatVnd(m.principal)}, lãi ${formatVnd(m.interest)}.`));
      }
      const divs = (ev?.upcoming ?? []).filter((e) => e.held && e.kind === "dividend_cash").slice(0, 4);
      lines.push(...divs.map((e) => `${e.symbol}: ${e.title}${e.key_date ? `, GDKHQ ${dmy(e.key_date)}` : ""}${e.payout ? `, trả ${dmy(e.payout)}` : ""}.`));
      if (!lines.length) lines.push("Chưa có số sổ tiết kiệm hay cổ tức sắp về.");
      return { title: "Tiền sắp về", lines, links: [{ label: "Sổ tài sản", href: "/profile?tab=tai-san" }, { label: "Lịch sự kiện", href: "/events" }] };
    }
    case "theses": {
      const t = await maybe<{ theses: { symbol: string; conditions: { status: string | null; view: { state: string } }[]; progress: { overdue: boolean; reached: boolean } | null }[]; missing: string[] }>("theses");
      if (!t) return { title: "Luận điểm", lines: ["Chưa đọc được luận điểm."], links: [] };
      const broken = t.theses.filter((x) => x.conditions.some((c) => c.status === "broken" || c.view.state === "broken")).map((x) => x.symbol);
      const overdue = t.theses.filter((x) => x.progress?.overdue && !x.progress.reached).map((x) => x.symbol);
      const lines = [broken.length ? `Có điều kiện bị phá: ${broken.join(", ")}.` : "Không luận điểm nào bị phá điều kiện.",
        ...(overdue.length ? [`Quá hạn mục tiêu mà chưa đạt: ${overdue.join(", ")}.`] : []),
        ...(t.missing.length ? [`Đang nắm nhưng chưa có luận điểm: ${t.missing.join(", ")}.`] : [])];
      return { title: "Luận điểm cần xem lại", lines, links: [{ label: "Luận điểm (Danh mục)", href: "/portfolio" },
        ...[...broken, ...overdue].slice(0, 3).map((s) => ({ label: `Trang 1 trang ${s}`, href: `/thesis/${s}` }))] };
    }
    case "report": {
      const r = await maybe<{ reports: { report_id: string; session_date: string; status: string }[] }>("reports");
      const latest = r?.reports[0];
      return latest ? { title: "Bản tin phiên gần nhất", lines: [`Phiên ${dmy(latest.session_date)}.`], links: [{ label: `Mở bản tin ${dmy(latest.session_date)}`, href: `/reports/${latest.report_id}` }, { label: "Tất cả bản tin", href: "/reports" }] }
        : { title: "Bản tin", lines: ["Chưa có bản tin nào."], links: [{ label: "Bản tin sau phiên", href: "/reports" }] };
    }
    case "health": {
      const h = await maybe<{ ok: boolean; problems: { label: string; detail: string }[]; last_finish: string | null }>("system-health");
      if (!h) return { title: "Sức khỏe hệ thống", lines: ["Chưa đọc được."], links: [] };
      return { title: h.ok ? "Hệ thống ổn" : `Có ${h.problems.length} vấn đề`, lines: h.ok ? [`Lượt chạy gần nhất xong ${h.last_finish ? dmy(h.last_finish) : "—"}.`]
        : h.problems.map((p) => `${p.label}: ${p.detail}.`), links: [{ label: "Cài đặt (sức khỏe hệ thống)", href: "/settings" }] };
    }
    case "stock": {
      const s = intent.symbol;
      const links = [{ label: `Trang ${s}`, href: `/research/${s}` }, { label: `Luận điểm 1 trang ${s}`, href: `/thesis/${s}` }];
      const w = await maybe<{ rows: { ticker: string; close: string | null; date: string | null; change_1d: string | null; change_20d: string | null; held: boolean }[] }>("watchlist");
      const row = w?.rows.find((r) => r.ticker === s);
      const lines = row ? [`Giá ${formatVnd(row.close)}${row.date ? ` (${dmy(row.date)})` : ""}: phiên ${signed(row.change_1d, 2)}, 20 phiên ${signed(row.change_20d, 1)}${row.held ? " · đang nắm" : ""}.`]
        : [`${s} không có trong danh sách theo dõi.`];
      if (row && intent.focus !== "price") {
        const m = await maybe<{ facts: Record<string, string[]>; bands: { rows: { name: string; low: string; mid: string | null; high: string }[] }; scenarios: { expected: string | null; upside: string | null } | null; lights: Record<string, number>; auto_catalysts: { when: string; text: string }[]; catalysts: { when: string; text: string; done: boolean }[] }>(`stock/${s}/model`);
        if (m && intent.focus === "valuation") {
          lines.push(...(m.facts.valuation ?? []));
          lines.push(...m.bands.rows.slice(0, 3).map((b) => `${b.name}: ${formatVnd(b.low)} – ${formatVnd(b.high)}${b.mid ? ` (giữa ${formatVnd(b.mid)})` : ""}.`));
          links.push({ label: "Định giá", href: "/fair-value" });
        } else if (m && intent.focus === "thesis") {
          lines.push(m.scenarios?.expected ? `Giá kỳ vọng ${formatVnd(m.scenarios.expected)} (${signed(m.scenarios.upside)}).` : "Chưa nhập kịch bản.",
            `Đèn: ${m.lights.good} tốt, ${m.lights.watch} theo dõi, ${m.lights.bad} xấu.`);
        } else if (m && intent.focus === "events") {
          const next = [...m.catalysts.filter((c) => !c.done), ...m.auto_catalysts].slice(0, 4);
          lines.push(...(next.length ? next.map((c) => `${c.when}: ${c.text}.`) : ["Chưa có sự kiện sắp tới."]));
          links.push({ label: "Lịch sự kiện", href: "/events" });
        }
      }
      return { title: s, lines, links };
    }
    case "go":
      return { title: "Mở trang", lines: intent.matches.length > 1 ? ["Có vài chỗ khớp:"] : [], links: intent.matches.map((d) => ({ label: d.label, href: d.href })) };
    default:
      return { title: "Mình chưa hiểu câu này", lines: ["Thử gõ một mã (FPT), \"định giá HPG\", \"sổ nào sắp đáo hạn\", \"cổ tức\", hoặc tên trang (\"thác nước\", \"radar\", \"quỹ mở\")."],
        links: [] };
  }
}

/** Trợ lý: a round button at the bottom right; its panel answers by keywords and quick buttons from data on this machine. */
export function Assistant() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([{ from: "bot", answer: HELLO }]);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { if (open && !symbols.length) maybe<{ rows: { ticker: string }[] }>("watchlist").then((w) => setSymbols(w?.rows.map((r) => r.ticker) ?? [])); }, [open, symbols.length]);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages]);
  const ask = async (q: string) => {
    if (!q.trim() || busy) return;
    setText(""); setBusy(true);
    setMessages((m) => [...m, { from: "me", text: q }]);
    const a = await answer(parse(q, symbols));
    setMessages((m) => [...m, { from: "bot", answer: a }]);
    setBusy(false);
  };
  return (
    <>
      <button type="button" className="as-fab" aria-label={open ? "Đóng trợ lý" : "Mở trợ lý"} title="Trợ lý" onClick={() => setOpen(!open)}>
        {open ? <X size={22} aria-hidden="true" /> : <Bot size={24} aria-hidden="true" />}</button>
      {open && <section className="as-panel" role="dialog" aria-label="Trợ lý">
        <header className="as-head"><Bot size={20} aria-hidden="true" /><div><strong>Trợ lý</strong><span className="caption">trên máy bạn · không dùng AI</span></div>
          <button type="button" className="btn as-x" aria-label="Đóng trợ lý" onClick={() => setOpen(false)}><X size={16} aria-hidden="true" /></button></header>
        <div className="as-body">
          {messages.map((m, i) => m.from === "me" ? <p key={i} className="as-me">{m.text}</p> : <div key={i} className="as-bot">
            <strong>{m.answer!.title}</strong>
            {m.answer!.lines.map((l, k) => <p key={k}>{l}</p>)}
            {m.answer!.links.length > 0 && <div className="as-links">{m.answer!.links.map((l) => <Link key={l.href + l.label} href={l.href} onClick={() => setOpen(false)}>{l.label} →</Link>)}</div>}
          </div>)}
          {busy && <p className="muted fx-loading" role="status">Đang tìm…</p>}
          <div className="as-quick">{QUICK.map((q) => <button key={q.label} type="button" className="btn" disabled={busy} onClick={() => void ask(q.ask)}>{q.label}</button>)}</div>
          <div ref={end} />
        </div>
        <form className="as-input" onSubmit={(e) => { e.preventDefault(); void ask(text); }}>
          <input aria-label="Câu hỏi cho trợ lý" placeholder="Gõ mã, câu hỏi hoặc tên trang…" value={text} onChange={(e) => setText(e.target.value)} maxLength={200} />
          <button type="submit" className="btn" aria-label="Gửi" disabled={busy || !text.trim()}><Send size={16} aria-hidden="true" /></button>
        </form>
      </section>}
    </>
  );
}
