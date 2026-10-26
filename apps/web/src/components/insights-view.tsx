"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type View = "favourable" | "neutral" | "unfavourable";
type Verdict = "cheap" | "fair" | "expensive" | "insufficient";
type Reason = { text: string; quote: string; page: number; source: string; title: string; url: string };
type Macro = { votes: Record<View, number>; consensus: View | "mixed" | "none"; reasons: Reason[] };
type Claim = { sector: string; effect: "benefit" | "harm"; reason: string; quote: string; page: number; source: string; title: string; url: string };
type Sector = { sector: string; benefit: number; harm: number; mixed: boolean; claims: Claim[];
  tickers: { symbol: string; verdict: Verdict; held: boolean }[]; held_warning: string[] };
type Report = { source: string; ref_id: string; title: string; url: string; published: string; status: "ok" | "no_text" | "no_reliable_claims" };
type Data = { summary: { reports: number; macro_now: Macro; macro_outlook: Macro; sectors: Sector[] }; reports: Report[];
  ssi: { title: string; kind: string; date: string; url: string }[]; run: { at: string; status: string; errors?: Record<string, string> } | null; ai_configured: boolean; window_days: number };

const CONSENSUS: Record<Macro["consensus"], { label: string; tone: string }> = {
  favourable: { label: "Thuận lợi", tone: "good" }, neutral: { label: "Trung tính", tone: "" }, unfavourable: { label: "Bất lợi", tone: "bad" },
  mixed: { label: "Chưa thống nhất", tone: "warn" }, none: { label: "Chưa có báo cáo", tone: "" },
};
const VIEW_LABEL: Record<View, string> = { favourable: "Thuận lợi", neutral: "Trung tính", unfavourable: "Bất lợi" };
const VERDICT: Record<Verdict, { label: string; tone: string }> = {
  cheap: { label: "Rẻ", tone: "good" }, fair: { label: "Hợp lý", tone: "" }, expensive: { label: "Đắt", tone: "bad" },
  insufficient: { label: "Chưa đủ dữ liệu", tone: "warn" },
};
const SOURCE: Record<string, string> = { acbs: "ACBS", worldbank: "World Bank" };
const STATUS: Record<Report["status"], string> = { ok: "Đã đọc", no_text: "Không trích được văn bản", no_reliable_claims: "Không có nhận định đáng tin" };
const STOPPED: Record<string, string> = { budget_exceeded: "đã hết ngân sách AI tháng này", key_missing: "chưa cấu hình AI",
  catalog_stale: "bảng giá model đã cũ", no_eligible_model: "không có model được duyệt khả dụng", policy_not_approved: "chính sách AI chưa duyệt",
  concurrency_cap: "một lượt gọi AI trước chưa kết thúc", catalog_unavailable: "không tải được bảng giá model từ OpenRouter" };
const FAILED: Record<string, string> = { download_failed: "không tải được tệp", request_over_budget: "báo cáo quá dài so với giới hạn mỗi lần gọi",
  provider_error: "nhà cung cấp AI lỗi", network_unavailable: "mất mạng", outcome_unknown: "không rõ kết quả lượt gọi AI", rate_limited: "AI đang quá tải" };
const day = (iso: string) => iso.slice(0, 10).split("-").reverse().join("/");

function MacroCard({ title, macro, total }: { title: string; macro: Macro; total: number }) {
  const c = CONSENSUS[macro.consensus];
  const votes = (Object.keys(VIEW_LABEL) as View[]).filter((v) => macro.votes[v] > 0).map((v) => `${VIEW_LABEL[v]} ${macro.votes[v]}/${total} báo cáo`);
  return (
    <section className="surface ins-card" aria-label={title}>
      <h2>{title}</h2>
      <p><span className={`pill ${c.tone}`}>{c.label}</span> {votes.length > 0 && <span className="caption">{votes.join(" · ")}</span>}</p>
      <ul className="ins-reasons">{macro.reasons.map((r, i) => (
        <li key={i}>{r.text} <span className="caption">— <a href={r.url} target="_blank" rel="noreferrer">{SOURCE[r.source] ?? r.source}, tr. {r.page}</a>
          {" "}«{r.quote}»</span></li>))}
      </ul>
    </section>
  );
}

function SectorRow({ s }: { s: Sector }) {
  const [more, setMore] = useState(false);
  const claims = more ? s.claims : s.claims.slice(0, 1);
  return (
    <tr>
      <td data-label="Ngành"><strong>{s.sector}</strong>{s.mixed && <div><span className="pill warn">Các nguồn khác ý</span></div>}</td>
      <td data-label="Hưởng lợi" className="num">{s.benefit}</td>
      <td data-label="Bất lợi" className="num">{s.harm}</td>
      <td data-label="Lý do">
        {claims.map((c, i) => (
          <div key={i} className="ins-claim"><span className={`pill ${c.effect === "benefit" ? "good" : "bad"}`}>{c.effect === "benefit" ? "Hưởng lợi" : "Bất lợi"}</span>
            {" "}{c.reason} <span className="caption">— <a href={c.url} target="_blank" rel="noreferrer">{SOURCE[c.source] ?? c.source}, tr. {c.page}</a> «{c.quote}»</span></div>))}
        {s.claims.length > 1 && <button className="btn" aria-expanded={more} onClick={() => setMore(!more)}>{more ? "Thu gọn" : `Xem thêm (${s.claims.length - 1})`}</button>}
      </td>
      <td data-label="Mã theo dõi">
        {s.tickers.length === 0 ? <span className="muted">—</span> : s.tickers.map((t) => (
          <span key={t.symbol} className="ins-ticker">{t.held ? <strong>{t.symbol}</strong> : t.symbol}{" "}
            <span className={`pill ${VERDICT[t.verdict].tone}`}>{VERDICT[t.verdict].label}</span>
            {s.held_warning.includes(t.symbol) && <span className="pill bad" title="Đang nắm mã thuộc ngành được đánh giá bất lợi">⚠ đang nắm</span>}</span>))}
      </td>
    </tr>
  );
}

export function InsightsView() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Data>("insights").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted">Đang tải…</p>;
  const { summary, run } = data;
  const stopped = run?.status.startsWith("stopped:") ? STOPPED[run.status.slice(8)] ?? run.status.slice(8) : null;
  return (
    <>
      <p className="notice">Tổng hợp tự động từ báo cáo công khai (ACBS, World Bank) trong {data.window_days} ngày gần nhất. AI chỉ đọc nội dung báo cáo;
        việc ghép với mã theo dõi và Định giá làm trên máy của bạn. Mỗi nhận định kèm câu trích nguyên văn để kiểm tra. Tham khảo, không phải khuyến nghị đầu tư.</p>
      {!data.ai_configured && <p className="errors" role="status">Chưa cấu hình AI: thêm OPENROUTER_API_KEY vào .env.local rồi khởi động lại ứng dụng.</p>}
      {stopped && <p className="errors" role="status">Lần chạy {day(run!.at)} dừng đọc báo cáo mới: {stopped}.</p>}
      {run?.errors && Object.keys(run.errors).length > 0 && <p className="caption" role="status">Lần chạy {day(run.at)}: {Object.keys(run.errors).length} báo cáo
        chưa đọc được ({[...new Set(Object.values(run.errors))].map((c) => FAILED[c] ?? c).join("; ")}); sẽ thử lại tối đa 3 lần.</p>}
      <div className="ins-grid">
        <MacroCard title="Vĩ mô hiện tại" macro={summary.macro_now} total={summary.reports} />
        <MacroCard title="Triển vọng 6–12 tháng" macro={summary.macro_outlook} total={summary.reports} />
      </div>
      <section className="surface">
        <h2>Ngành hưởng lợi và bất lợi</h2>
        {summary.sectors.length === 0 ? <p className="muted">Chưa có nhận định về ngành.</p> : (
          <table className="fv-table ins-table" aria-label="Ngành hưởng lợi và bất lợi">
            <thead><tr><th>Ngành</th><th className="num">Hưởng lợi</th><th className="num">Bất lợi</th><th>Lý do</th><th>Mã theo dõi</th></tr></thead>
            <tbody>{summary.sectors.map((s) => <SectorRow key={s.sector} s={s} />)}</tbody>
          </table>)}
        <p className="caption">Số trong cột Hưởng lợi / Bất lợi là số báo cáo nói như vậy. Mã đậm là mã đang nắm.</p>
      </section>
      <section className="surface">
        <h2>Báo cáo đã đọc</h2>
        {data.reports.length === 0 ? <p className="muted">Chưa đọc báo cáo nào.</p> : (
          <ul className="ins-list" aria-label="Báo cáo đã đọc">{data.reports.map((r) => (
            <li key={`${r.source}-${r.ref_id}`}><span className="caption">{SOURCE[r.source] ?? r.source} · {day(r.published)}</span>{" "}
              <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a>{" "}
              <span className={`pill ${r.status === "ok" ? "good" : "warn"}`}>{STATUS[r.status]}</span></li>))}
          </ul>)}
      </section>
      <section className="surface">
        <h2>Tiêu đề mới từ SSI</h2>
        <p className="caption">Chỉ tiêu đề (tải báo cáo SSI cần đăng nhập); không dùng để kết luận.</p>
        {data.ssi.length === 0 ? <p className="muted">Chưa có.</p> : (
          <ul className="ins-list" aria-label="Tiêu đề SSI">{data.ssi.map((t) => (
            <li key={t.url}><span className="caption">SSI vừa ra báo cáo {t.kind} · {day(t.date)}:</span>{" "}
              <a href={t.url} target="_blank" rel="noreferrer">{t.title}</a></li>))}
          </ul>)}
      </section>
    </>
  );
}
