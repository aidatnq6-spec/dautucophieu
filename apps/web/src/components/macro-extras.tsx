"use client";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";
import { parseFx, parseRate, spreadPath, swapCost } from "../lib/macro-extras";

type Point = { date: string; vnd: string; usd: string; usd_source: "SOFR" | "EFFR"; spread: string };
type Spread = { points: Point[]; latest: Point | null; days: number; negative_days: number };
type Kind = "fed" | "sbv" | "data" | "fiscal" | "other";
type Event = { id: string; date: string; title: string; kind: Kind; note: string; source: string; remind: boolean; reminded_on?: string | null; days?: number };
type Events = { version: number; coming: Event[]; past: Event[]; kinds: Record<Kind, string> };

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const pct = (v: number | string, digits = 2) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const signed = (v: string) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${pct(Math.abs(Number(v)))}`;
const failure = (e: unknown, fallback: string) => (e instanceof ApiError ? e.failure.message : fallback);
const W = 600, H = 120, SHOWN = 120;

/** V1 Chênh lệch lãi suất VND–USD and V7 the swap calculator, which starts from the latest USD overnight rate stored. */
export function RateSpread() {
  const [s, setS] = useState<Spread | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Spread>("macro/spread").then(setS, (e) => setError(failure(e, "Lỗi tải."))); }, []);
  const points = s ? s.points.slice(-SHOWN) : [];
  const path = spreadPath(points, W, H);
  const l = s?.latest;
  return (
    <>
      <section className="surface" aria-label="Chênh lệch lãi suất VND–USD">
        <h2>Chênh lệch lãi suất VND–USD</h2>
        <p className="caption">Lãi suất liên ngân hàng qua đêm bình quân của NHNN trừ lãi suất USD qua đêm cùng ngày (SOFR; chưa có thì EFFR của Fed;
          số USD cũ hơn 7 ngày không dùng). Chênh lệch âm: giữ VND được trả lãi thấp hơn giữ USD, tiền dễ chuyển sang USD và tạo áp lực lên tỷ giá.</p>
        {error && <p className="errors" role="alert">{error}</p>}
        {!s && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
        {s && !l && <p className="muted">Chưa có số liệu: cần cả lãi suất liên ngân hàng qua đêm và lãi suất USD qua đêm của cùng ngày.</p>}
        {s && l && <>
          {Number(l.spread) < 0 && <p className="notice" role="status">Chênh lệch đang âm ({signed(l.spread)} điểm %): lãi VND qua đêm thấp hơn lãi USD.</p>}
          <p data-testid="spread-latest"><strong>{signed(l.spread)} điểm %</strong> <span className="caption">ngày {dmy(l.date)}: VND {pct(l.vnd)}% − USD {pct(l.usd)}% ({l.usd_source})</span></p>
          <p className="caption">{s.negative_days} trong {s.days} ngày có số bị âm.</p>
          {points.length > 1 && <svg className="sp-chart" viewBox={`-4 -4 ${W + 8} ${H + 8}`} role="img"
            aria-label={`Chênh lệch ${points.length} ngày gần nhất, từ ${dmy(points[0].date)} đến ${dmy(l.date)}`}>
            <line x1={0} x2={W} y1={path.zero} y2={path.zero} className="sp-zero" />
            <polyline points={path.line} className="sp-line" fill="none" />
          </svg>}
          {points.length > 1 && <p className="caption">Đường ngang là mức 0; {points.length} ngày gần nhất có đủ hai số.</p>}
        </>}
      </section>
      <SwapCalculator usd={l ? { rate: l.usd, source: l.usd_source, date: l.date } : null} />
    </>
  );
}

function SwapCalculator({ usd }: { usd: { rate: string; source: string; date: string } | null }) {
  const [f, setF] = useState({ spot: "", forward: "", months: "6", usd: "" });
  const usdText = f.usd || (usd ? usd.rate.replace(".", ",") : "");
  const c = swapCost({ spot: parseFx(f.spot), forward: parseFx(f.forward), months: Number(f.months), usdRate: parseRate(usdText) });
  return (
    <section className="surface" aria-label="Chi phí hoán đổi ngoại tệ">
      <h2>Chi phí hoán đổi ngoại tệ</h2>
      <p className="caption">Nhập tỷ giá giao ngay và tỷ giá kỳ hạn của một giao dịch hoán đổi (ví dụ NHNN công bố). Chi phí hoán đổi một năm
        = (kỳ hạn ÷ giao ngay − 1) × 12 ÷ số tháng; chi phí vốn VND = lãi suất USD + chi phí hoán đổi (ngang giá lãi suất có bảo hiểm).</p>
      <form className="formgrid" aria-label="Tính chi phí hoán đổi" onSubmit={(e) => e.preventDefault()}>
        <label className="field">Tỷ giá giao ngay<input aria-label="Tỷ giá giao ngay" inputMode="decimal" value={f.spot} onChange={(e) => setF({ ...f, spot: e.target.value })} /></label>
        <label className="field">Tỷ giá kỳ hạn<input aria-label="Tỷ giá kỳ hạn" inputMode="decimal" value={f.forward} onChange={(e) => setF({ ...f, forward: e.target.value })} /></label>
        <label className="field">Kỳ hạn (tháng)<input aria-label="Kỳ hạn (tháng)" type="number" min={1} max={60} value={f.months} onChange={(e) => setF({ ...f, months: e.target.value })} /></label>
        <label className="field">Lãi suất USD (%/năm)<input aria-label="Lãi suất USD" inputMode="decimal" value={usdText} onChange={(e) => setF({ ...f, usd: e.target.value })} /></label>
      </form>
      {!f.usd && usd && <p className="caption">Lãi suất USD lấy sẵn {usd.source} ngày {dmy(usd.date)}; sửa nếu giao dịch dùng lãi suất khác.</p>}
      {c ? <ul className="perf-bench" aria-label="Kết quả hoán đổi">
        <li>Chênh tỷ giá kỳ hạn: <strong>{pct(c.premium)}%</strong> cho {f.months} tháng</li>
        <li>Chi phí hoán đổi một năm: <strong>{pct(c.annual)}%/năm</strong></li>
        <li>Chi phí vốn VND tương đương: {c.vnd === null ? <span className="muted">cần lãi suất USD</span> : <strong>{pct(c.vnd)}%/năm</strong>}</li>
      </ul> : <p className="muted">Nhập đủ tỷ giá giao ngay, tỷ giá kỳ hạn và kỳ hạn để tính.</p>}
    </section>
  );
}

const blank = { date: "", title: "", kind: "sbv" as Kind, note: "", source: "", remind: true };
const asSent = (e: Event) => ({ id: e.id, date: e.date, title: e.title, kind: e.kind, note: e.note, source: e.source, remind: e.remind });

/** V5 Lịch và nhật ký vĩ mô: the owner records each event with its source; nothing is filled in from elsewhere. */
export function MacroCalendar() {
  const [ev, setEv] = useState<Events | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(blank);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api<Events>("macro/events").then(setEv, (e) => setError(failure(e, "Lỗi tải."))); }, []);
  const all = ev ? [...ev.past, ...ev.coming] : [];
  const save = async (events: object[]) => {
    if (!ev) return false;
    setBusy(true); setError(null);
    try { setEv(await api<Events>("macro/events", { method: "PUT", body: { events, expected_version: ev.version, request_id: requestId() } })); return true; }
    catch (e) { setError(failure(e, "Không lưu được.")); return false; } finally { setBusy(false); }
  };
  const add = async () => {
    if (!form.date || !form.title.trim()) { setError("Nhập ngày và nội dung sự kiện."); return; }
    if (await save([...all.map(asSent), { id: requestId().slice(0, 32), ...form }])) setForm(blank);
  };
  const drop = (id: string) => void save(all.filter((e) => e.id !== id).map(asSent));
  const row = (e: Event, coming: boolean) => <tr key={e.id}>
    <td data-label="Ngày">{dmy(e.date)}{coming && <div className="caption">{e.days === 0 ? "hôm nay" : `còn ${e.days} ngày`}</div>}</td>
    <td data-label="Loại"><span className="pill">{ev!.kinds[e.kind]}</span></td>
    <td data-label="Nội dung">{e.title}{e.note && <div className="caption">{e.note}</div>}</td>
    <td data-label="Nguồn">{/^https?:\/\//.test(e.source) ? <a href={e.source} target="_blank" rel="noreferrer">{e.source.replace(/^https?:\/\/(www\.)?/, "").slice(0, 40)}</a>
      : e.source || <span className="muted">chưa ghi nguồn</span>}</td>
    <td data-label="Nhắc">{coming ? (e.remind ? (e.reminded_on ? "Đã nhắc" : "Nhắc trước 1 ngày") : "—") : ""}</td>
    <td><button type="button" className="btn text" disabled={busy} onClick={() => drop(e.id)} aria-label={`Xóa ${e.title}`}>Xóa</button></td>
  </tr>;
  const head = <thead><tr><th>Ngày</th><th>Loại</th><th>Nội dung</th><th>Nguồn</th><th>Nhắc</th><th /></tr></thead>;
  return (
    <section className="surface" aria-label="Lịch và nhật ký vĩ mô">
      <h2>Lịch và nhật ký vĩ mô</h2>
      <p className="caption">Ghi các cuộc họp Fed, nghiệp vụ của NHNN (hoán đổi, OMO, điều chỉnh tỷ giá trung tâm) và ngày công bố số liệu, kèm nguồn.
        Ứng dụng không tự điền ngày; sự kiện có đánh dấu nhắc được báo qua Telegram một lần, trước một ngày.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!ev && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {ev && <>
        <form className="formgrid" aria-label="Thêm sự kiện vĩ mô" onSubmit={(e) => { e.preventDefault(); void add(); }}>
          <label className="field">Ngày<input aria-label="Ngày sự kiện" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></label>
          <label className="field">Loại<select aria-label="Loại sự kiện" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as Kind })}>
            {(Object.keys(ev.kinds) as Kind[]).map((k) => <option key={k} value={k}>{ev.kinds[k]}</option>)}</select></label>
          <label className="field">Nội dung<input aria-label="Nội dung sự kiện" maxLength={160} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
          <label className="field">Ghi chú<input aria-label="Ghi chú sự kiện" maxLength={300} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
          <label className="field">Nguồn (link hoặc tên)<input aria-label="Nguồn sự kiện" maxLength={160} value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} /></label>
          <label className="db-check"><input type="checkbox" checked={form.remind} onChange={(e) => setForm({ ...form, remind: e.target.checked })} />Nhắc trước 1 ngày</label>
          <button type="submit" className="btn" disabled={busy}>Thêm sự kiện</button>
        </form>
        <h3>Sắp tới</h3>
        {ev.coming.length === 0 ? <p className="muted">Chưa có sự kiện sắp tới.</p>
          : <table className="fv-table" aria-label="Sự kiện vĩ mô sắp tới">{head}<tbody>{ev.coming.map((e) => row(e, true))}</tbody></table>}
        {ev.past.length > 0 && <details><summary>Nhật ký đã qua ({ev.past.length})</summary>
          <table className="fv-table" aria-label="Nhật ký vĩ mô đã qua">{head}<tbody>{ev.past.map((e) => row(e, false))}</tbody></table></details>}
      </>}
    </section>
  );
}
