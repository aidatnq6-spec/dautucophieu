"use client";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";
import Link from "next/link";
import { type Catalyst, type Question, ThesisCatalysts, ThesisQuestions } from "./thesis-questions";
import { type Band, type Bands, ValuationBands } from "./valuation-bands";

type Name = "bad" | "base" | "good";
type Scenario = { name: Name; price: string; prob: string; note: string };
type Tier = "lead" | "coincident" | "lag" | "valuation";
export type Indicator = { id: string; name: string; tier: Tier; unit: string; bad: string; base: string; good: string; lower_better: boolean; source: string;
  readings: { period: string; value: string }[] };
type Model = { scenarios: Scenario[]; review: { when: string; on: string | null }; indicators: Indicator[]; questions: Record<string, Question>;
  catalysts: Catalyst[]; stage: "draft" | "reviewed"; updated_on: string | null; headline: string; summary: string;
  ranges: Omit<Band, "auto">[] };
type Row = Indicator & { current: string | null; period: string | null; grade: "good" | "watch" | "bad" | null };
type View = { symbol: string; version: number; model: Model; close: string | null; close_date: string | null;
  scenarios: { rows: (Scenario & { upside: string | null })[]; expected: string | null; upside: string | null; review: Model["review"]; review_due: boolean } | null;
  indicators: Row[]; lights: Record<"good" | "watch" | "bad" | "none", number>; auto_metrics: Record<string, { label: string; unit: string }>;
  catalysts_due: string[]; updated_on: string | null; bands: Bands };

const SCEN_LABEL: Record<Name, string> = { bad: "Xấu", base: "Cơ sở", good: "Tốt" };
const TIER: Record<Tier, string> = { lead: "Dẫn", coincident: "Đồng hành", lag: "Sau", valuation: "Định giá" };
const GRADE: Record<"good" | "watch" | "bad", [string, string]> = { good: ["Tốt", "good"], watch: ["Theo dõi", "warn"], bad: ["Xấu", "bad"] };
const num = (v: string) => v.trim().replace(/\./g, "").replace(",", ".");
const dec = (v: string) => v.trim().replace(",", ".");
const signed = (v: string | null) => (v === null ? "—" : `${Number(v) > 0 ? "+" : ""}${formatRatio(v, 1)}`);

/** The weighted price of three scenarios as typed (đồng, probabilities in percent); null unless all three are filled and add to 100. */
export function weighted(rows: { price: string; prob: string }[]): number | null {
  if (rows.length !== 3 || rows.some((r) => !r.price || !r.prob)) return null;
  const total = rows.reduce((a, r) => a + Number(dec(r.prob)), 0);
  if (Math.abs(total - 100) > 1e-9) return null;
  return Math.round(rows.reduce((a, r) => a + Number(num(r.price)) * Number(dec(r.prob)) / 100, 0));
}

export function ThesisModel({ symbol }: { symbol: string }) {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [scen, setScen] = useState<Scenario[] | null>(null);
  const [review, setReview] = useState<Model["review"]>({ when: "", on: null });
  const [adding, setAdding] = useState<Indicator | null>(null);
  const [reading, setReading] = useState<Record<string, { period: string; value: string }>>({});
  const [head, setHead] = useState<{ headline: string; summary: string } | null>(null);
  const [range, setRange] = useState<{ name: string; low: string; mid: string; high: string; source: string }>({ name: "", low: "", mid: "", high: "", source: "" });
  useEffect(() => {
    api<View>(`stock/${encodeURIComponent(symbol)}/model`).then((v) => { setView(v); setReview(v.model.review); },
      (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, [symbol]);
  if (error && !view) return null;  // not a watched ticker
  if (!view) return null;
  const save = async (model: Model) => {
    setBusy(true); setError(null);
    try {
      const v = await api<View>(`stock/${encodeURIComponent(symbol)}/model`, { method: "PUT", body: { ...model, expected_version: view.version, request_id: requestId() } });
      setView(v); setReview(v.model.review); setScen(null); setAdding(null); setReading({});
    } catch (e) { setError(e instanceof ApiError ? e.failure.message : "Không lưu được."); } finally { setBusy(false); }
  };
  const model = view.model, s = view.scenarios;
  const draft = scen ?? (model.scenarios.length ? model.scenarios : (["bad", "base", "good"] as Name[]).map((name) => ({ name, price: "", prob: "", note: "" })));
  const preview = scen ? weighted(scen) : null;
  const blankIndicator = (): Indicator => ({ id: requestId().slice(0, 24), name: "", tier: "coincident", unit: "", bad: "", base: "", good: "", lower_better: false,
    source: "manual", readings: [] });
  return (
    <section className="surface" id="kich-ban-chi-bao" aria-label="Kịch bản và chỉ báo luận điểm">
      <div className="row"><h2>Kịch bản và chỉ báo luận điểm</h2><Link href={`/thesis/${symbol}`}>Trang luận điểm 1 trang để in</Link></div>
      {head ? <div className="formgrid" aria-label="Sửa tiêu đề và tóm tắt">
        <label className="field">Tiêu đề luận điểm<input aria-label="Tiêu đề luận điểm" maxLength={200} value={head.headline} onChange={(e) => setHead({ ...head, headline: e.target.value })} /></label>
        <label className="field">Tóm tắt<textarea aria-label="Tóm tắt luận điểm" maxLength={800} rows={3} value={head.summary} onChange={(e) => setHead({ ...head, summary: e.target.value })} /></label>
        <div className="ib-actions"><button type="button" className="btn" disabled={busy} onClick={() => void save({ ...view.model, ...head }).then(() => setHead(null))}>Lưu</button>
          <button type="button" className="btn" onClick={() => setHead(null)}>Hủy</button></div>
      </div> : <div className="tm-head">{view.model.headline ? <p className="tm-headline">{view.model.headline}</p> : <p className="muted">Chưa có tiêu đề luận điểm.</p>}
        {view.model.summary && <p>{view.model.summary}</p>}
        <button type="button" className="btn" onClick={() => setHead({ headline: view.model.headline ?? "", summary: view.model.summary ?? "" })}>Sửa tiêu đề và tóm tắt</button></div>}
      {error && <p className="errors" role="alert">{error}</p>}
      <div className="tm-tiles">
        <div><span className="caption">Giá {view.close_date ? `${view.close_date.slice(8, 10)}/${view.close_date.slice(5, 7)}` : ""}</span><strong>{formatVnd(view.close)}</strong></div>
        <div><span className="caption">Giá kỳ vọng (3 kịch bản)</span><strong data-testid="tm-expected">{s?.expected ? formatVnd(s.expected) : "—"}</strong></div>
        <div><span className="caption">Tiềm năng so giá hiện tại</span><strong className={s?.upside && Number(s.upside) >= 0 ? "fd-up" : "fd-down"}>{signed(s?.upside ?? null)}</strong></div>
        <div><span className="caption">Đèn theo dõi</span><strong data-testid="tm-lights">{view.lights.good} tốt · {view.lights.watch} theo dõi · {view.lights.bad} xấu</strong></div>
      </div>
      {s?.review_due && <p className="notice" role="note">Đến ngày xem lại kịch bản: {s.review.when || s.review.on}.</p>}

      {view.updated_on && <p className="caption">Cập nhật {view.updated_on.split("-").reverse().join("/")}.</p>}
      <ThesisQuestions model={model} save={save} busy={busy} />
      <h3>Ba kịch bản</h3>
      <table className="fv-table" aria-label="Ba kịch bản">
        <thead><tr><th>Kịch bản</th><th className="num">Giá (đ/CP)</th><th className="num">Xác suất</th><th className="num">So giá hiện tại</th><th>Giả định</th></tr></thead>
        <tbody>{draft.map((r, i) => <tr key={r.name}><td data-label="Kịch bản">{SCEN_LABEL[r.name]}</td>
          {scen ? <>
            <td className="num" data-label="Giá"><input aria-label={`Giá ${SCEN_LABEL[r.name]}`} inputMode="numeric" value={r.price}
              onChange={(e) => setScen(draft.map((x, j) => (j === i ? { ...x, price: e.target.value } : x)))} /></td>
            <td className="num" data-label="Xác suất"><input aria-label={`Xác suất ${SCEN_LABEL[r.name]}`} inputMode="decimal" value={r.prob}
              onChange={(e) => setScen(draft.map((x, j) => (j === i ? { ...x, prob: e.target.value } : x)))} /></td>
            <td className="num" data-label="So giá hiện tại">—</td>
            <td data-label="Giả định"><input aria-label={`Giả định ${SCEN_LABEL[r.name]}`} maxLength={200} value={r.note}
              onChange={(e) => setScen(draft.map((x, j) => (j === i ? { ...x, note: e.target.value } : x)))} /></td>
          </> : <>
            <td className="num" data-label="Giá">{r.price ? formatVnd(r.price) : "—"}</td><td className="num" data-label="Xác suất">{r.prob ? `${r.prob}%` : "—"}</td>
            <td className="num" data-label="So giá hiện tại">{signed(s?.rows.find((x) => x.name === r.name)?.upside ?? null)}</td><td data-label="Giả định">{r.note}</td></>}
        </tr>)}</tbody>
      </table>
      {scen ? <div className="ib-actions">
        <label className="field">Xem lại khi<input aria-label="Xem lại khi" maxLength={200} value={review.when} onChange={(e) => setReview({ ...review, when: e.target.value })} /></label>
        <label className="field">Ngày xem lại<input aria-label="Ngày xem lại" type="date" value={review.on ?? ""} onChange={(e) => setReview({ ...review, on: e.target.value || null })} /></label>
        <span className="caption">{preview === null ? "Nhập đủ ba giá và xác suất cộng 100%." : `Giá kỳ vọng: ${formatVnd(String(preview))}`}</span>
        <button type="button" className="btn" disabled={busy} onClick={() => void save({ ...model, review, scenarios: scen.map((r) => ({ ...r, price: num(r.price), prob: dec(r.prob) })) })}>Lưu kịch bản</button>
        <button type="button" className="btn" onClick={() => { setScen(null); setReview(model.review); }}>Hủy</button>
        {model.scenarios.length > 0 && <button type="button" className="btn" disabled={busy} onClick={() => void save({ ...model, scenarios: [] })}>Xóa kịch bản</button>}
      </div> : <p className="caption">{model.review.when ? `Xem lại khi: ${model.review.when}${model.review.on ? ` (${model.review.on.split("-").reverse().join("/")})` : ""}. ` : ""}
        <button type="button" className="btn" onClick={() => setScen(draft)}>{model.scenarios.length ? "Sửa kịch bản" : "Nhập kịch bản"}</button></p>}

      <h3>Định giá: khoảng theo từng cách</h3>
      <ValuationBands bands={view.bands} />
      {(model.ranges ?? []).length > 0 && <ul className="tm-ranges">{model.ranges.map((r) => <li key={r.id}><em>{r.name}</em>: {formatVnd(r.low)} – {formatVnd(r.high)}
        {r.mid ? ` (giữa ${formatVnd(r.mid)})` : ""}{r.source ? ` · ${r.source}` : ""} <button type="button" className="btn tq-x" aria-label={`Xóa khoảng ${r.name}`} disabled={busy}
          onClick={() => void save({ ...model, ranges: model.ranges.filter((x) => x.id !== r.id) })}>×</button></li>)}</ul>}
      <form className="formgrid" aria-label="Thêm khoảng định giá" onSubmit={(e) => { e.preventDefault();
        void save({ ...model, ranges: [...(model.ranges ?? []), { id: requestId().slice(0, 24), name: range.name, low: num(range.low), mid: range.mid ? num(range.mid) : null,
          high: num(range.high), source: range.source }] }).then(() => setRange({ name: "", low: "", mid: "", high: "", source: "" })); }}>
        <label className="field">Cách định giá<input aria-label="Tên cách định giá" placeholder="SOTP, EV/EBITDA, CTCK…" maxLength={40} value={range.name}
          onChange={(e) => setRange({ ...range, name: e.target.value })} /></label>
        <label className="field">Thấp (đ)<input aria-label="Giá thấp" inputMode="numeric" value={range.low} onChange={(e) => setRange({ ...range, low: e.target.value })} /></label>
        <label className="field">Giữa (đ)<input aria-label="Giá giữa" inputMode="numeric" value={range.mid} onChange={(e) => setRange({ ...range, mid: e.target.value })} /></label>
        <label className="field">Cao (đ)<input aria-label="Giá cao" inputMode="numeric" value={range.high} onChange={(e) => setRange({ ...range, high: e.target.value })} /></label>
        <label className="field">Nguồn<input aria-label="Nguồn khoảng" maxLength={120} value={range.source} onChange={(e) => setRange({ ...range, source: e.target.value })} /></label>
        <button type="submit" className="btn" disabled={busy || !range.name.trim() || !range.low || !range.high}>Thêm khoảng</button>
      </form>
      <h3>Chỉ báo theo dõi</h3>
      {view.indicators.length > 0 && <table className="fv-table" aria-label="Chỉ báo theo dõi">
        <thead><tr><th>Chỉ báo</th><th>Tầng</th><th className="num">Hiện tại</th><th className="num">Xấu</th><th className="num">Cơ sở</th><th className="num">Tốt</th><th>Đánh giá</th><th /></tr></thead>
        <tbody>{view.indicators.map((r) => <tr key={r.id}>
          <td data-label="Chỉ báo">{r.name}{r.unit && <span className="caption"> ({r.unit})</span>}<div className="caption">{r.source === "manual" ? "bạn nhập" : "tự động từ báo cáo"}
            {r.lower_better ? " · thấp là tốt" : ""}</div></td>
          <td data-label="Tầng">{TIER[r.tier]}</td>
          <td className="num" data-label="Hiện tại">{r.current === null ? "—" : formatDecimal(r.current, 1)}{r.period && <div className="caption">{r.period}</div>}</td>
          <td className="num" data-label="Xấu">{formatDecimal(r.bad, 1)}</td><td className="num" data-label="Cơ sở">{formatDecimal(r.base, 1)}</td>
          <td className="num" data-label="Tốt">{formatDecimal(r.good, 1)}</td>
          <td data-label="Đánh giá">{r.grade ? <span className={`pill ${GRADE[r.grade][1]}`}>{GRADE[r.grade][0]}</span> : "chưa có số"}</td>
          <td data-label="Thao tác"><div className="ib-actions">
            {r.source === "manual" && <>
              <input aria-label={`Kỳ ${r.name}`} placeholder="2026-Q4" maxLength={20} value={reading[r.id]?.period ?? ""}
                onChange={(e) => setReading({ ...reading, [r.id]: { period: e.target.value, value: reading[r.id]?.value ?? "" } })} />
              <input aria-label={`Số ${r.name}`} placeholder="số" inputMode="decimal" value={reading[r.id]?.value ?? ""}
                onChange={(e) => setReading({ ...reading, [r.id]: { period: reading[r.id]?.period ?? "", value: e.target.value } })} />
              <button type="button" className="btn" disabled={busy || !reading[r.id]?.value} onClick={() => void save({ ...model, indicators: model.indicators.map((x) => (x.id === r.id
                ? { ...x, readings: [...x.readings, { period: reading[r.id].period, value: dec(reading[r.id].value) }] } : x)) })}>Ghi số</button></>}
            <button type="button" className="btn" aria-label={`Xóa chỉ báo ${r.name}`} disabled={busy}
              onClick={() => { if (window.confirm(`Xóa chỉ báo ${r.name}?`)) void save({ ...model, indicators: model.indicators.filter((x) => x.id !== r.id) }); }}>Xóa</button>
          </div></td></tr>)}</tbody>
      </table>}
      <ThesisCatalysts model={model} save={save} busy={busy} due={view.catalysts_due} />
      {adding ? <form className="formgrid" aria-label="Thêm chỉ báo" onSubmit={(e) => { e.preventDefault(); void save({ ...model, indicators: [...model.indicators,
        { ...adding, bad: dec(adding.bad), base: dec(adding.base), good: dec(adding.good) }] }); }}>
        <label className="field">Nguồn<select aria-label="Nguồn chỉ báo" value={adding.source} onChange={(e) => {
          const src = e.target.value, auto = view.auto_metrics[src.replace("auto:", "")];
          setAdding({ ...adding, source: src, ...(auto ? { name: adding.name || auto.label, unit: auto.unit } : {}) });
        }}><option value="manual">Bạn nhập theo kỳ</option>
          {Object.entries(view.auto_metrics).map(([k, m]) => <option key={k} value={`auto:${k}`}>Tự động: {m.label}</option>)}</select></label>
        <label className="field">Tên<input aria-label="Tên chỉ báo" maxLength={80} value={adding.name} onChange={(e) => setAdding({ ...adding, name: e.target.value })} /></label>
        <label className="field">Tầng<select aria-label="Tầng" value={adding.tier} onChange={(e) => setAdding({ ...adding, tier: e.target.value as Tier })}>
          {(Object.keys(TIER) as Tier[]).map((t) => <option key={t} value={t}>{TIER[t]}</option>)}</select></label>
        <label className="field">Đơn vị<input aria-label="Đơn vị" maxLength={12} value={adding.unit} onChange={(e) => setAdding({ ...adding, unit: e.target.value })} /></label>
        <label className="field">Mức Xấu<input aria-label="Mức Xấu" inputMode="decimal" value={adding.bad} onChange={(e) => setAdding({ ...adding, bad: e.target.value })} /></label>
        <label className="field">Mức Cơ sở<input aria-label="Mức Cơ sở" inputMode="decimal" value={adding.base} onChange={(e) => setAdding({ ...adding, base: e.target.value })} /></label>
        <label className="field">Mức Tốt<input aria-label="Mức Tốt" inputMode="decimal" value={adding.good} onChange={(e) => setAdding({ ...adding, good: e.target.value })} /></label>
        <label className="db-check"><input type="checkbox" checked={adding.lower_better} onChange={(e) => setAdding({ ...adding, lower_better: e.target.checked })} />Thấp là tốt</label>
        <button type="submit" className="btn" disabled={busy}>Lưu chỉ báo</button><button type="button" className="btn" onClick={() => setAdding(null)}>Hủy</button>
      </form> : <button type="button" className="btn" onClick={() => setAdding(blankIndicator())}>Thêm chỉ báo</button>}
      <p className="caption">Giá kỳ vọng = tổng giá từng kịch bản × xác suất; tiềm năng so với giá đóng cửa gần nhất. Đánh giá theo quy tắc của bạn: Tốt khi bằng hoặc vượt mức
        Cơ sở, Xấu khi chạm mức Xấu, ở giữa là Theo dõi; mức Tốt là mốc vươn tới. Chỉ báo tự động lấy từ báo cáo đã công bố (tỷ đồng, %, lần); chỉ báo bạn nhập lấy số ghi gần
        nhất. Đèn chuyển Xấu hoặc đến ngày xem lại thì báo một lần qua Telegram sau phiên. Không phải khuyến nghị.</p>
    </section>
  );
}
