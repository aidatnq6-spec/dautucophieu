"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Summary = { n: number; n_independent: number; mean: string | null; median: string | null; win_rate: string | null; t: string | null;
  p10?: string | null; p90?: string | null; dip_median?: string | null; dip_worst?: string | null; enough?: boolean };
type PeGroup = Summary & { bucket: number; label: string; pe_low: string | null; pe_high: string | null };
type Dot = { date: string; pe: string; change: string; bucket: number };
type PeStats = { h: number; groups: PeGroup[]; all: Summary; scatter: Dot[]; trend: { slope: string; intercept: string; r2: string } | null;
  today: { date: string; pe: string; position: string; bucket: number } | null; from: string | null };
type LightGroup = Summary & { level: "green" | "yellow" | "red" };
type Light = { id: string; name: string; h: number; groups: LightGroup[]; all: Summary; today: "green" | "yellow" | "red" | null; from: string | null };
type Shock = Summary & { id: string; label: string; events: number; recent: string[]; today: boolean };
export type HistoryStats = { h: number; horizons: number[]; pe: PeStats; lights: Light[]; shocks?: { h: number; groups: Shock[]; all: Summary; from: string | null }; summary?: string };

const LEVEL = { green: "Bình thường", yellow: "Cảnh báo", red: "Nguy hiểm" } as const;
const num = (v: number, d: number) => v.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** A change as a signed percentage, "—" without samples. */
export function changePct(v: string | null): string {
  if (v === null) return "—";
  const x = Number(v) * 100;
  return `${x > 0 ? "+" : x < 0 ? "−" : ""}${num(Math.abs(x), 1)}%`;
}

/** How much a group's figures can be leaned on: few independent windows, or a t under 2, is said plainly. */
export function evidence(s: Summary): string {
  if (s.n === 0) return "chưa có mẫu";
  if (s.n_independent < 5) return `chỉ ${s.n_independent} khoảng độc lập: rất ít`;
  if (s.t === null || Math.abs(Number(s.t)) < 2) return `${s.n_independent} khoảng độc lập, chưa rõ khác 0`;
  return `${s.n_independent} khoảng độc lập, t = ${num(Number(s.t), 1)}`;
}

/** Fewer than 5 independent windows: the figures are not shown, only that the period has too little data. */
export function enough(s: Summary): boolean {
  return s.enough ?? s.n_independent >= 5;
}

function Row({ label, s, mark }: { label: string; s: Summary; mark?: boolean }) {
  const ok = enough(s);
  const cell = (v: string | null | undefined) => (ok ? changePct(v ?? null) : "—");
  return (
    <tr className={mark ? "hs-today" : undefined}>
      <td data-label="Nhóm">{label}{mark && <span className="pill good"> hôm nay</span>}</td>
      <td className="num" data-label="Số mẫu">{s.n}</td>
      <td className="num" data-label="Không chồng lấn">{s.n_independent}</td>
      {ok ? <>
        <td className={`num ${s.mean && Number(s.mean) > 0 ? "positive" : s.mean && Number(s.mean) < 0 ? "negative" : ""}`} data-label="Trung bình">{changePct(s.mean)}</td>
        <td className="num" data-label="Trung vị">{changePct(s.median)}</td>
        <td className="num" data-label="Tỷ lệ tăng">{s.win_rate === null ? "—" : `${num(Number(s.win_rate) * 100, 0)}%`}</td>
        <td className="num" data-label="Xấu thường gặp (P10)">{cell(s.p10)}</td>
        <td className="num" data-label="Tốt thường gặp (P90)">{cell(s.p90)}</td>
        <td className="num negative" data-label="Giảm sâu nhất trong kỳ: trung vị">{cell(s.dip_median)}</td>
        <td className="num negative" data-label="Giảm sâu nhất trong kỳ: tệ nhất">{cell(s.dip_worst)}</td>
        <td data-label="Độ tin cậy" className="caption">{evidence(s)}</td>
      </> : <td colSpan={8} className="caption" data-label="Kết quả">{s.n === 0 ? "chưa có mẫu" : "không đủ dữ liệu cho kỳ này"}</td>}
    </tr>
  );
}

const HEAD = <thead><tr><th>Nhóm</th><th className="num">Số mẫu</th><th className="num">Không chồng lấn</th><th className="num">Trung bình</th>
  <th className="num">Trung vị</th><th className="num">Tỷ lệ tăng</th><th className="num">Xấu thường gặp (P10)</th><th className="num">Tốt thường gặp (P90)</th>
  <th className="num">Giảm sâu nhất trong kỳ: trung vị</th><th className="num">Giảm sâu nhất trong kỳ: tệ nhất</th><th>Độ tin cậy</th></tr></thead>;

function Scatter({ pe }: { pe: PeStats }) {
  if (pe.scatter.length < 3) return null;
  const W = 900, H = 300, L = 46, R = 12, T = 10, B = 28;
  const xs = pe.scatter.map((d) => Number(d.pe)), ys = pe.scatter.map((d) => Number(d.change));
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys, 0), y1 = Math.max(...ys, 0);
  const X = (v: number) => L + ((v - x0) / (x1 - x0 || 1)) * (W - L - R), Y = (v: number) => T + (1 - (v - y0) / (y1 - y0 || 1)) * (H - T - B);
  const tr = pe.trend, todayPe = pe.today ? Number(pe.today.pe) : null;
  return (
    <svg className="hs-scatter" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="P/E lúc đó và VN-Index sau đó">
      <line x1={L} x2={W - R} y1={Y(0)} y2={Y(0)} className="hs-axis" />
      {[y0, 0, y1].map((v) => <text key={v} x={L - 6} y={Y(v) + 4} className="hs-tick" textAnchor="end">{changePct(String(v))}</text>)}
      {[x0, (x0 + x1) / 2, x1].map((v) => <text key={v} x={X(v)} y={H - 8} className="hs-tick" textAnchor="middle">{num(v, 1)}</text>)}
      {pe.scatter.map((d) => <circle key={d.date} cx={X(Number(d.pe))} cy={Y(Number(d.change))} r={2.6} className={Number(d.change) >= 0 ? "hs-up" : "hs-down"} />)}
      {tr && <line x1={X(x0)} x2={X(x1)} y1={Y(Number(tr.intercept) + Number(tr.slope) * x0)} y2={Y(Number(tr.intercept) + Number(tr.slope) * x1)} className="hs-trend" />}
      {todayPe !== null && todayPe >= x0 && todayPe <= x1 && <line x1={X(todayPe)} x2={X(todayPe)} y1={T} y2={H - B} className="hs-now" />}
    </svg>
  );
}

type Condition = { id: string; label: string; kind: "monthly" | "daily"; state: boolean | null; known_on: string | null; figure_date: string | null; from: string | null };
type StateRow = Summary & { a: boolean; b: boolean };
export type States = { h: number; rows: StateRow[]; all: Summary; today: { a: boolean; b: boolean } | null; from: string | null; runs: [string, string][];
  a: { id: string; label: string }; b: { id: string; label: string }; fx: string; conditions: Condition[]; line: { date: string; close: string }[] };

/** The figure a condition stands on: a month for the World Bank series, a day for the daily ones. */
export function figureText(c: Condition): string {
  if (!c.figure_date) return "chưa có số";
  return c.kind === "monthly" ? `số tháng ${c.figure_date.slice(5, 7)}/${c.figure_date.slice(0, 4)}` : `số ngày ${dmy(c.figure_date)}`;
}

function StateChart({ s }: { s: States }) {
  if (s.line.length < 3) return null;
  const W = 900, H = 220, L = 46, R = 10, T = 8, B = 22;
  const t0 = Date.parse(s.line[0].date), t1 = Date.parse(s.line[s.line.length - 1].date);
  const ys = s.line.map((p) => Number(p.close)), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const X = (iso: string) => L + ((Date.parse(iso) - t0) / (t1 - t0 || 1)) * (W - L - R), Y = (v: number) => T + (1 - (v - y0) / (y1 - y0 || 1)) * (H - T - B);
  return (
    <svg className="hs-scatter" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Giai đoạn cả hai điều kiện cùng đúng, trên VN-Index">
      {s.runs.filter(([a]) => a >= s.line[0].date).map(([a, b]) => <rect key={a} x={X(a)} y={T} width={Math.max(1, X(b) - X(a))} height={H - T - B} className="hs-run" />)}
      <polyline points={s.line.map((p) => `${X(p.date)},${Y(Number(p.close))}`).join(" ")} className="hs-line" />
      {[y0, y1].map((v) => <text key={v} x={L - 6} y={Y(v) + 4} className="hs-tick" textAnchor="end">{num(v, 0)}</text>)}
      {[s.line[0].date, s.line[s.line.length - 1].date].map((d, i) => <text key={d} x={X(d)} y={H - 6} className="hs-tick" textAnchor={i ? "end" : "start"}>{d.slice(0, 4)}</text>)}
    </svg>
  );
}

const FX = ["0.5", "1", "2", "3"];

/** Trạng thái vĩ mô 2×2: two conditions chosen by the owner, VN-Index h sessions later in the four combinations. */
function StatesView({ h }: { h: number }) {
  const [a, setA] = useState("cpi_up"), [b, setB] = useState("fx_up"), [fx, setFx] = useState("1");
  const [loaded, setData] = useState<States | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api<States>(`history-stats/states/${h}/${a}/${b}/${fx}`).then((d) => { if (live) setData(d); }, (e) => { if (live) setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."); });
    return () => { live = false; };
  }, [h, a, b, fx]);
  const s = loaded && loaded.h === h && loaded.a.id === a && loaded.b.id === b && loaded.fx === fx ? loaded : null;
  const options = (loaded?.conditions ?? []).map((c) => <option key={c.id} value={c.id}>{c.label}</option>);
  const yes = (v: boolean) => (v ? "có" : "không");
  return (
    <section className="surface" aria-label="Trạng thái vĩ mô hai điều kiện">
      <h2>Trạng thái vĩ mô: hai điều kiện</h2>
      <p className="caption">Mỗi điều kiện chỉ tính từ khi số đã công bố: CPI, sản xuất công nghiệp, xuất khẩu tháng M (World Bank, từ 2010) từ ngày 10 tháng sau;
        tỷ giá bình quân tháng từ ngày 1 tháng sau; số ngày của FRED từ hôm sau. Lãi suất trong nước chưa có nguồn lịch sử công khai nên chưa có điều kiện này;
        lợi suất Mỹ 10 năm là của Mỹ, không thay thế lãi suất Việt Nam.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {loaded && <div className="formgrid">
        <label className="field">Điều kiện A<select value={a} onChange={(e) => setA(e.target.value)}>{options}</select></label>
        <label className="field">Điều kiện B<select value={b} onChange={(e) => setB(e.target.value)}>{options}</select></label>
        <div className="field">Ngưỡng tỷ giá trong 3 tháng<div className="chips" role="radiogroup" aria-label="Ngưỡng tỷ giá">{FX.map((x) =>
          <button key={x} type="button" role="radio" aria-checked={fx === x} className={`chip${fx === x ? " on" : ""}`} onClick={() => setFx(x)}>{x.replace(".", ",")}%</button>)}</div></div>
      </div>}
      {a === b && <p className="notice">Chọn hai điều kiện khác nhau.</p>}
      {!s && !error && a !== b && <p className="muted fx-loading" role="status">Đang tính…</p>}
      {s && <>
        <table className="fv-table" aria-label="Vĩ mô hôm nay">
          <thead><tr><th>Điều kiện</th><th>Hôm nay</th><th>Số liệu</th><th>Có từ</th></tr></thead>
          <tbody>{s.conditions.map((c) => <tr key={c.id}><td data-label="Điều kiện">{c.label}</td>
            <td data-label="Hôm nay">{c.state === null ? <span className="muted">chưa biết</span> : <strong>{c.state ? "Đúng" : "Không"}</strong>}</td>
            <td data-label="Số liệu" className="caption">{figureText(c)}</td><td data-label="Có từ" className="caption">{c.from ? dmy(c.from) : "—"}</td></tr>)}</tbody>
        </table>
        <table className="fv-table" aria-label="VN-Index sau đó theo hai điều kiện">{HEAD}
          <tbody>{s.rows.map((r) => <Row key={`${r.a}${r.b}`} label={`A ${yes(r.a)}, B ${yes(r.b)}`} s={r} mark={!!s.today && s.today.a === r.a && s.today.b === r.b} />)}
            <Row label="Mọi lúc" s={s.all} /></tbody>
        </table>
        <p className="caption">A: {s.a.label}. B: {s.b.label}. Có từ {s.from ? dmy(s.from) : "—"}.{s.today ? "" : " Hôm nay chưa biết đủ cả hai điều kiện."}</p>
        <StateChart s={s} />
        <p className="caption">Vùng tô là các giai đoạn cả A và B cùng đúng; đường là VN-Index theo tuần.</p>
      </>}
    </section>
  );
}

/** Thống kê lịch sử: VN-Index some sessions later by P/E group and by the macro lights' levels, with the evidence each rests on. */
export function HistoryStatsView() {
  const [h, setH] = useState(250);
  const [loaded, setData] = useState<HistoryStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api<HistoryStats>(`history-stats/${h}`).then((d) => { if (live) setData(d); }, (e) => { if (live) setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."); });
    return () => { live = false; };
  }, [h]);
  const data = loaded && loaded.h === h ? loaded : null;  // a figure of another horizon is never shown under this one
  return (
    <>
      <section className="surface" aria-label="Số phiên nhìn tới">
        {data?.summary && <p className="hs-summary" data-testid="history-summary">{data.summary}
          <span className="caption"> (câu viết theo mẫu từ chính các số trên trang, không dùng AI)</span></p>}
        <div className="chips" role="radiogroup" aria-label="VN-Index sau bao nhiêu phiên">
          {(data?.horizons ?? [20, 60, 120, 250, 500]).map((x) => <button key={x} type="button" role="radio" aria-checked={h === x} className={`chip${h === x ? " on" : ""}`}
            onClick={() => setH(x)}>{x} phiên</button>)}
        </div>
        <p className="caption">Mỗi phiên trong quá khứ được xếp theo trạng thái đã biết ngay hôm đó, rồi xem VN-Index {h} phiên sau. Các khoảng {h} phiên của
          những ngày liền nhau gối lên nhau, nên ngoài số mẫu còn ghi số <strong>khoảng không chồng lấn</strong> (cách nhau ít nhất {h} phiên); thống kê t chỉ
          tính trên các khoảng đó. Nhóm có dưới 5 khoảng không chồng lấn thì không hiện số. P10 là kết quả xấu thường gặp (1 trong 10 lần tệ hơn), P90 là
          kết quả tốt thường gặp; &ldquo;giảm sâu nhất trong kỳ&rdquo; là mức VN-Index thấp nhất so với ngày vào trong {h} phiên sau đó. Kết quả quá khứ không bảo
          đảm tương lai; không phải khuyến nghị.</p>
      </section>
      {error && <p className="errors" role="alert">{error}</p>}
      {!data && !error && <p className="muted fx-loading" role="status">Đang tính…</p>}
      {data && <>
        <section className="surface" aria-label="Mua ở mức P/E này thì sau đó ra sao">
          <h2>Mua ở mức P/E này thì sau đó thường ra sao?</h2>
          {data.pe.today && <p>Hôm nay ({dmy(data.pe.today.date)}) P/E VN-Index <strong>{num(Number(data.pe.today.pe), 2)}</strong>, cao hơn hoặc bằng{" "}
            {num(Number(data.pe.today.position) * 100, 0)}% số phiên 5 năm trước đó: nhóm <strong>{data.pe.groups[data.pe.today.bucket].label.toLowerCase()}</strong>.</p>}
          <p className="caption">Nhóm theo vị trí P/E so với 5 năm trước chính ngày đó (cần ít nhất 250 phiên), không theo toàn bộ lịch sử, để không dùng số của
            tương lai; vì vậy khoảng P/E của các nhóm gối lên nhau. P/E VN-Index có từ 12/2017{data.pe.from ? `, nhóm có từ ${dmy(data.pe.from)}` : ""}.</p>
          <Scatter pe={data.pe} />
          {data.pe.trend && <p className="caption">Đường xu hướng: R² = {num(Number(data.pe.trend.r2), 2)} (P/E giải thích được khoảng {num(Number(data.pe.trend.r2) * 100, 0)}%
            biến động của VN-Index {h} phiên sau). Vạch dọc là P/E hôm nay.</p>}
          <table className="fv-table" aria-label="VN-Index sau đó theo nhóm P/E">{HEAD}
            <tbody>{data.pe.groups.map((g) => <Row key={g.bucket} label={`${g.label}${g.pe_low ? ` (P/E ${num(Number(g.pe_low), 1)}–${num(Number(g.pe_high), 1)})` : ""}`}
              s={g} mark={data.pe.today?.bucket === g.bucket} />)}
              <Row label="Mọi lúc" s={data.pe.all} /></tbody>
          </table>
        </section>
        {data.shocks && <section className="surface" aria-label="Sau một cú sốc thì sao">
          <h2>Sau một cú sốc thì sao?</h2>
          <p className="caption">Các ngày VN-Index gặp một cú sốc, và VN-Index {h} phiên sau đó. Cú giảm 20% tính từ đỉnh 52 tuần (250 phiên), chỉ ngày đầu tiên
            vượt ngưỡng; cắt xuống trung bình 200 phiên chỉ ngày đầu tiên đóng cửa dưới đường đó. VN-Index có từ {data.shocks.from ? dmy(data.shocks.from) : "—"}.</p>
          <table className="fv-table" aria-label="VN-Index sau cú sốc">{HEAD}
            <tbody>{data.shocks.groups.map((sh) => <Row key={sh.id} label={`${sh.label} (${sh.events} lần${sh.recent.length ? `, gần nhất ${dmy(sh.recent[sh.recent.length - 1])}` : ""})`}
              s={sh} mark={sh.today} />)}
              <Row label="Mọi lúc" s={data.shocks.all} /></tbody>
          </table>
        </section>}
        <StatesView h={h} />
        <section className="surface" aria-label="Kiểm tra ngưỡng đèn bằng lịch sử">
          <h2>Kiểm tra ngưỡng Đèn tín hiệu rủi ro vĩ mô</h2>
          <p className="caption">Mức của mỗi đèn tính đúng như trên trang Vĩ mô với ngưỡng bạn đã duyệt, cho từng ngày trong quá khứ. Một ngưỡng có ích khi
            nhóm &ldquo;Nguy hiểm&rdquo; đi kèm VN-Index kém hơn hẳn &ldquo;Mọi lúc&rdquo;, với đủ khoảng độc lập.</p>
          {data.lights.map((lg) => (
            <div key={lg.id} data-testid={`light-history-${lg.id}`}>
              <h3>{lg.name} {lg.today && <span className="caption">· hôm nay {LEVEL[lg.today].toLowerCase()}</span>}
                <span className="caption"> · {lg.from ? `có từ ${dmy(lg.from)}` : "chưa có lịch sử"}</span></h3>
              <table className="fv-table" aria-label={`VN-Index sau đó theo mức đèn ${lg.name}`}>{HEAD}
                <tbody>{lg.groups.map((g) => <Row key={g.level} label={LEVEL[g.level]} s={g} mark={lg.today === g.level} />)}
                  <Row label="Mọi lúc" s={lg.all} /></tbody>
              </table>
            </div>
          ))}
        </section>
      </>}
    </>
  );
}
