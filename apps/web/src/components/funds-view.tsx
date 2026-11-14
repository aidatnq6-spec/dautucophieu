"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

export type Kind = "STOCK" | "BALANCED" | "BOND";
type Returns = { ytd: string | null; m1: string | null; m3: string | null; m6: string | null; m12: string | null; m36: string | null; m60: string | null; annual36: string | null };
type Place = { rank: number; of: number } | null;
export type Fund = { code: string; name: string; kind: Kind | null; manager: string | null; fee: string | null; nav: string; date: string;
  returns: Returns | null; held: boolean; beats_deposit: boolean | null; rank?: { m6: Place; m12: Place }; run_up?: boolean | null; score?: Score | null };
type Score = { score: string | null; parts: { returns: string | null; fee: string | null; risk: string | null }; counted: string[]; risk_days: number;
  peers: number; trend: { previous: string; change: string } | null };
const PART_LABEL: Record<string, string> = { returns: "hiệu suất", fee: "phí", risk: "rủi ro" };

/** Điểm khách quan: the score, its arrow against last month, and what it is made of. */
export function scoreView(s: Score | null | undefined): { text: string; arrow: string; title: string } {
  if (!s || s.score === null) return { text: "—", arrow: "", title: s && s.peers < 2 ? "Quỹ duy nhất trong nhóm: không so được" : "Chưa đủ số để chấm" };
  const change = s.trend ? Number(s.trend.change) : null;
  const arrow = change === null ? "" : change > 0 ? `▲${formatDecimal(s.trend!.change, 1)}` : change < 0 ? `▼${formatDecimal(s.trend!.change.replace("-", ""), 1)}` : "=";
  const parts = s.counted.map((k) => `${PART_LABEL[k]} ${formatDecimal(s.parts[k as keyof Score["parts"]]!, 0)}`).join(", ");
  const risk = s.parts.risk === null ? `; rủi ro chưa tính (có ${s.risk_days} ngày NAV, cần 120)` : "";
  return { text: formatDecimal(s.score, 0), arrow, title: `${parts}${risk}` };
}
type Group = { kind: Kind | "unknown"; value: string; share: string; funds: string[] };
type Mine = { groups: Group[]; total: string; fund_count: number; at_cost: string[]; notes: ("fewer_than_3" | "single_kind")[] };
type ThroughRow = { symbol: string; direct: string; through: string; total: string; share: string | null; funds: { code: string; percent: string }[] };
type Through = { rows: ThroughRow[]; base: string; unvalued: string[]; unpriced: string[]; covered: Record<string, { as_of: string | null; stocks: string; bonds: string }> };
type Board = { funds: Fund[]; counts: Record<Kind, number>; through?: Through;
  benchmark: { vnindex: { as_of: string | null; ytd: string | null; m12: string | null; m36: string | null; m60: string | null }; deposit_12m: string | null };
  mine: Mine; source: { name: string; fetched_at: string } | null; history_days: Record<string, number> };

export const KIND_LABEL: Record<Kind | "unknown", string> = { STOCK: "Cổ phiếu", BALANCED: "Cân bằng", BOND: "Trái phiếu", unknown: "Chưa rõ nhóm" };
const FILTERS: { id: Kind | "all"; label: string }[] = [
  { id: "all", label: "Tất cả" }, { id: "STOCK", label: "Cổ phiếu" }, { id: "BALANCED", label: "Cân bằng" }, { id: "BOND", label: "Trái phiếu" }];
const PERIODS: { key: "ytd" | "m12" | "m36" | "m60"; label: string }[] = [
  { key: "ytd", label: "Từ đầu năm" }, { key: "m12", label: "1 năm" }, { key: "m36", label: "3 năm" }, { key: "m60", label: "5 năm" }];
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** A return in percent ("-9.64") as "−9,64%", "+" when above zero; "—" when the source has none. */
export function returnText(v: string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const text = `${formatDecimal(v, 2)}%`;
  return Number(v) > 0 ? `+${text}` : text;
}

const tone = (v: string | null | undefined) => (v == null || Number(v) === 0 ? undefined : Number(v) > 0 ? "fd-up" : "fd-down");

/** The warnings under the owner's split: the two the webinar names, plus funds counted at cost. */
export function mineNotes(mine: Mine): string[] {
  const out: string[] = [];
  if (mine.notes.includes("fewer_than_3")) out.push(`Bạn đang giữ ${mine.fund_count} quỹ: ít hơn 3 quỹ thì một quỹ đi sai hướng ảnh hưởng lớn đến cả phần quỹ.`);
  if (mine.notes.includes("single_kind")) out.push(`Toàn bộ nằm trong một nhóm (${KIND_LABEL[mine.groups[0].kind]}): chưa có nhóm khác để cân lại khi thị trường đổi chiều.`);
  if (mine.at_cost.length) out.push(`Chưa có NAV của ${mine.at_cost.join(", ")}: tính theo vốn đã mua và chưa rõ nhóm.`);
  return out;
}

/** Kiểm tra mua đỉnh: how far the fund rose over 6 and 12 months and where that puts it among the funds of its kind. */
export function runUpCheck(f: Fund): { text: string; warn: boolean } {
  const kind = f.kind ? `quỹ ${KIND_LABEL[f.kind].toLowerCase()}` : "quỹ cùng nhóm";
  const place = (p: Place) => (p ? `, cao thứ ${p.rank}/${p.of} ${kind}` : "");
  const m6 = f.returns?.m6 ?? null, m12 = f.returns?.m12 ?? null;
  if (m6 === null && m12 === null) return { text: `${f.code}: Fmarket chưa có lợi nhuận 6 và 12 tháng (quỹ mới hoặc thiếu số), chưa kiểm tra được.`, warn: false };
  const text = `${f.code} 6 tháng ${returnText(m6)}${place(f.rank?.m6 ?? null)}; 12 tháng ${returnText(m12)}${place(f.rank?.m12 ?? null)} (NAV ngày ${day(f.date)}).`;
  return f.run_up
    ? { text: `${text} Quỹ vừa tăng mạnh: nằm trong nhóm một phần tư tăng nhiều nhất 6 tháng qua. Mua vì đã tăng dễ là mua đỉnh; hãy chắc lý do mua không chỉ là mức tăng này.`, warn: true }
    : { text, warn: false };
}

let boardOnce: Promise<Board> | null = null;
const loadBoard = () => (boardOnce ??= api<Board>("funds").catch((e) => { boardOnce = null; throw e; }));

/** The check for one fund code, as typed in Sổ tài sản; nothing for a code Fmarket does not list. */
export function FundCheck({ code }: { code: string }) {
  const [board, setBoard] = useState<Board | null>(null);
  useEffect(() => { loadBoard().then(setBoard, () => setBoard(null)); }, []);
  const fund = board?.funds.find((f) => f.code === code.trim().toUpperCase());
  if (!fund) return null;
  const c = runUpCheck(fund);
  return <p className={c.warn ? "notice" : "caption"} role="note" data-testid="fund-check">Kiểm tra mua đỉnh: {c.text}</p>;
}

function MineSection({ mine }: { mine: Mine }) {
  return (
    <section className="surface" aria-label="Quỹ của bạn theo nhóm">
      <h2>Quỹ của bạn theo nhóm</h2>
      {mine.groups.length === 0 ? <p className="muted">Chưa có dòng quỹ nào trong Sổ tài sản (dòng trái phiếu/chứng chỉ quỹ có mã quỹ và số đơn vị).</p> : <>
        <div className="fd-bar" role="img" aria-label={mine.groups.map((g) => `${KIND_LABEL[g.kind]} ${formatRatio(g.share, 1)}`).join(", ")}>
          {mine.groups.map((g) => <span key={g.kind} className={`fd-seg fd-${g.kind.toLowerCase()}`} style={{ flexGrow: Number(g.share) }} />)}
        </div>
        <table className="fv-table" aria-label="Cơ cấu quỹ của bạn">
          <thead><tr><th>Nhóm</th><th className="num">Giá trị theo NAV</th><th className="num">Tỷ trọng</th><th>Quỹ</th></tr></thead>
          <tbody>{mine.groups.map((g) => <tr key={g.kind}>
            <td data-label="Nhóm"><span className={`fd-dot fd-${g.kind.toLowerCase()}`} aria-hidden="true" />{KIND_LABEL[g.kind]}</td>
            <td className="num" data-label="Giá trị theo NAV">{formatVnd(g.value)}</td>
            <td className="num" data-label="Tỷ trọng">{formatRatio(g.share, 1)}</td>
            <td data-label="Quỹ">{g.funds.join(", ")}</td></tr>)}</tbody>
        </table>
        {mineNotes(mine).map((n) => <p key={n} className="notice" role="note">{n}</p>)}
      </>}
      <p className="caption">Lấy từ các dòng có mã quỹ trong Sổ tài sản (Hồ sơ &amp; rủi ro), tính theo số đơn vị × NAV mới nhất. Sổ tài sản vẫn xếp chứng chỉ quỹ vào lớp
        trái phiếu của Tháp tài sản, kể cả quỹ cổ phiếu: phần này chỉ để xem cơ cấu, không đổi Tháp tài sản. Không phải khuyến nghị.</p>
    </section>
  );
}

const month = (ym: string | null) => (ym ? `${ym.slice(5, 7)}/${ym.slice(0, 4)}` : "—");

/** Which published holdings of the owner's funds were counted: "DCDS 10/2026 (10 mã lớn nhất, 55,7% NAV)". */
export function coveredText(covered: Through["covered"]): string {
  return Object.entries(covered).map(([code, c]) => `${code} ${month(c.as_of)}: cổ phiếu công bố ${formatDecimal(c.stocks, 1)}% NAV`
    + (Number(c.bonds) > 0 ? `, trái phiếu ${formatDecimal(c.bonds, 1)}%` : "")).join("; ");
}

function ThroughSection({ through }: { through: Through }) {
  const viaFunds = through.rows.filter((r) => Number(r.through) > 0);
  return (
    <section className="surface" aria-label="Cổ phiếu bạn nắm qua quỹ">
      <h2>Cổ phiếu bạn nắm qua quỹ</h2>
      {viaFunds.length === 0 ? <p className="muted">Chưa có: các quỹ bạn giữ chưa có danh mục công bố, hoặc Sổ tài sản chưa có dòng quỹ.</p> : <>
        <table className="fv-table" aria-label="Cổ phiếu trực tiếp và qua quỹ">
          <thead><tr><th>Mã</th><th className="num">Nắm trực tiếp</th><th className="num">Qua quỹ</th><th className="num">Cộng</th>
            <th className="num">Tỷ trọng</th><th>Quỹ đang nắm (% NAV)</th></tr></thead>
          <tbody>{through.rows.map((r) => <tr key={r.symbol}>
            <td data-label="Mã"><strong>{r.symbol}</strong></td>
            <td className="num" data-label="Nắm trực tiếp">{formatVnd(r.direct)}</td>
            <td className="num" data-label="Qua quỹ">{formatVnd(r.through)}</td>
            <td className="num" data-label="Cộng">{formatVnd(r.total)}</td>
            <td className="num" data-label="Tỷ trọng">{r.share === null ? "—" : formatRatio(r.share, 1)}</td>
            <td data-label="Quỹ đang nắm">{r.funds.map((f) => `${f.code} ${formatDecimal(f.percent, 2)}%`).join(", ") || "—"}</td></tr>)}</tbody>
        </table>
        <p className="caption">Tỷ trọng trên tổng cổ phiếu nắm trực tiếp và giá trị các quỹ ({formatVnd(through.base)}). Qua quỹ = giá trị quỹ × tỷ trọng mã đó trong
          NAV theo danh mục công bố. Chỉ tính các mã lớn nhất mỗi quỹ công bố trên Fmarket ({coveredText(through.covered)}); phần còn lại của quỹ chưa biết nên
          không cộng.{through.unvalued.length ? ` Chưa có NAV, không tính: ${through.unvalued.join(", ")}.` : ""}{through.unpriced.length
            ? ` Chưa có giá, không tính phần trực tiếp: ${through.unpriced.join(", ")}.` : ""}</p>
      </>}
    </section>
  );
}

/** Qua quỹ bạn giữ, on a stock's page: the owner's funds whose published holdings include it. */
export function FundsHoldingStock({ symbol }: { symbol: string }) {
  const [view, setView] = useState<{ funds: { code: string; name: string; percent: string; as_of: string | null; amount: string }[]; fund_rows: number } | null>(null);
  useEffect(() => { api<NonNullable<typeof view>>(`funds/holding/${encodeURIComponent(symbol)}`).then(setView, () => setView(null)); }, [symbol]);
  if (!view || view.fund_rows === 0) return null;
  return (
    <section className="surface" aria-label="Qua quỹ bạn giữ">
      <h2>Qua quỹ bạn giữ</h2>
      {view.funds.length === 0 ? <p className="muted">Không quỹ nào bạn giữ có {symbol} trong danh mục công bố (các mã lớn nhất mỗi quỹ).</p>
        : <ul>{view.funds.map((f) => <li key={f.code}><strong>{f.code}</strong> ({f.name}): {symbol} chiếm {formatDecimal(f.percent, 2)}% NAV kỳ {month(f.as_of)},
          tương ứng khoảng {formatVnd(f.amount)} trong phần quỹ của bạn.</li>)}</ul>}
      <p className="caption">Theo danh mục quỹ công bố trên Fmarket, chỉ gồm các mã lớn nhất; xem tổng ở trang Quỹ mở.</p>
    </section>
  );
}

function BuyCheckSection({ funds }: { funds: Fund[] }) {
  const [code, setCode] = useState("");
  const fund = funds.find((f) => f.code === code);
  const c = fund ? runUpCheck(fund) : null;
  return (
    <section className="surface" aria-label="Kiểm tra mua đỉnh">
      <h2>Kiểm tra trước khi mua quỹ</h2>
      <label className="field sv-pick">Quỹ định mua<select aria-label="Quỹ định mua" value={code} onChange={(e) => setCode(e.target.value)}>
        <option value="">Chọn quỹ</option>
        {funds.map((f) => <option key={f.code} value={f.code}>{f.code} · {f.name}</option>)}</select></label>
      {c && <p className={c.warn ? "notice" : undefined} role="note" data-testid="fund-check">{c.text}</p>}
      <p className="caption">So lợi nhuận 6 và 12 tháng của quỹ với các quỹ cùng nhóm. Cảnh báo khi 6 tháng qua quỹ tăng và nằm trong một phần tư đứng đầu nhóm.
        Chỉ để nhìn lại, không chặn việc mua và không phải khuyến nghị.</p>
    </section>
  );
}

export type SortKey = "score" | "ytd" | "m12" | "m36" | "m60" | "fee";
export const SORTS: { id: SortKey; label: string }[] = [{ id: "score", label: "Điểm" }, { id: "ytd", label: "Từ đầu năm" }, { id: "m12", label: "1 năm" },
  { id: "m36", label: "3 năm" }, { id: "m60", label: "5 năm" }, { id: "fee", label: "Phí thấp nhất" }];
const KIND_ORDER: (Kind | null)[] = ["STOCK", "BALANCED", "BOND", null];

const sortValue = (f: Fund, key: SortKey): number | null => {
  if (key === "score") return f.score?.score != null ? Number(f.score.score) : null;
  if (key === "fee") return f.fee !== null ? -Number(f.fee) : null;  // lower fee ranks higher
  const v = f.returns?.[key];
  return v != null ? Number(v) : null;
};
export const isNewFund = (f: Fund) => f.returns?.m36 == null;

/** The table's order: by kind; within it the owner's funds first (when pinned), funds with three years of history before new ones,
 * then by the chosen measure (missing last), ties by three-year return. top: each fund's place among the first three of its kind. */
export function orderFunds(funds: Fund[], key: SortKey, pinHeld: boolean): { list: Fund[]; top: Record<string, number> } {
  const cmp = (a: Fund, b: Fund) => {
    const ka = KIND_ORDER.indexOf(a.kind), kb = KIND_ORDER.indexOf(b.kind);
    if (ka !== kb) return ka - kb;
    if (pinHeld && a.held !== b.held) return a.held ? -1 : 1;
    if (isNewFund(a) !== isNewFund(b)) return isNewFund(a) ? 1 : -1;
    const va = sortValue(a, key), vb = sortValue(b, key);
    if (va === null || vb === null) { if (va !== vb) return va === null ? 1 : -1; }
    else if (va !== vb) return vb - va;
    return (Number(b.returns?.m36 ?? -1e9)) - (Number(a.returns?.m36 ?? -1e9)) || a.code.localeCompare(b.code);
  };
  const list = [...funds].sort(cmp);
  const top: Record<string, number> = {};
  for (const kind of KIND_ORDER) {
    const ranked = funds.filter((f) => f.kind === kind && sortValue(f, key) !== null).sort((a, b) => sortValue(b, key)! - sortValue(a, key)!);
    ranked.slice(0, 3).forEach((f, i) => { top[f.code] = i + 1; });
  }
  return { list, top };
}

const STORE = "funds-sort";
function loadSort(): { key: SortKey; pin: boolean } {
  try { const v = JSON.parse(localStorage.getItem(STORE) ?? "null"); if (v && SORTS.some((s) => s.id === v.key)) return { key: v.key, pin: v.pin !== false }; } catch { /* no storage */ }
  return { key: "score", pin: true };
}

export function FundsView() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<Kind | "all">("all");
  const [sort, setSort] = useState<{ key: SortKey; pin: boolean }>(loadSort);  // the saved choice; the first screen is the loading line either way
  const changeSort = (next: { key: SortKey; pin: boolean }) => { setSort(next); try { localStorage.setItem(STORE, JSON.stringify(next)); } catch { /* no storage */ } };
  useEffect(() => { api<Board>("funds").then(setBoard, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!board) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const ordered = orderFunds(board.funds.filter((f) => kind === "all" || f.kind === kind), sort.key, sort.pin);
  const shown = ordered.list;
  const vn = board.benchmark.vnindex, deposit = board.benchmark.deposit_12m;
  const days = Math.max(0, ...Object.values(board.history_days));
  return (
    <>
      <MineSection mine={board.mine} />
      {board.through && <ThroughSection through={board.through} />}
      <BuyCheckSection funds={board.funds} />
      <section className="surface" aria-label="Bảng quỹ mở">
        <h2>Bảng quỹ mở</h2>
        {board.funds.length === 0 ? <p className="muted">Chưa có số quỹ: lịch chạy sau phiên lấy NAV từ Fmarket lúc 08:30, 15:30 và 20:00.</p> : <>
          <div className="sv-layers" role="radiogroup" aria-label="Nhóm quỹ">
            {FILTERS.map((f) => <label key={f.id} className={kind === f.id ? "on" : undefined}>
              <input type="radio" name="fd-kind" checked={kind === f.id} onChange={() => setKind(f.id)} />
              {f.label} ({f.id === "all" ? board.funds.length : board.counts[f.id]})</label>)}
          </div>
          <p data-testid="fund-benchmark">
            So sánh: VN-Index {PERIODS.map((p) => `${p.label.toLowerCase()} ${returnText(vn[p.key])}`).join(", ")}
            {vn.as_of ? ` (đến ${day(vn.as_of)})` : ""}; lãi gửi 12 tháng {deposit === null ? "chưa có" : `${formatDecimal(deposit, 2)}%/năm`}.
          </p>
          <div className="fd-sortbar">
            <label className="field">Sắp xếp theo<select aria-label="Sắp xếp theo" value={sort.key} onChange={(e) => changeSort({ ...sort, key: e.target.value as SortKey })}>
              {SORTS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
            <label className="db-check"><input type="checkbox" checked={sort.pin} onChange={(e) => changeSort({ ...sort, pin: e.target.checked })} />Quỹ đang nắm lên đầu</label>
            <span className="caption">Trong mỗi nhóm: quỹ đủ 3 năm lịch sử đứng trước quỹ mới.</span>
          </div>
          <table className="fv-table" aria-label="Danh sách quỹ mở">
            <thead><tr><th>Quỹ</th><th>Nhóm</th><th className="num">NAV/đơn vị</th>{PERIODS.map((p) => <th key={p.key} className="num" aria-sort={sort.key === p.key ? "descending" : undefined}>
              <button type="button" className={`fd-th${sort.key === p.key ? " on" : ""}`} onClick={() => changeSort({ ...sort, key: p.key })}>{p.label}{sort.key === p.key ? " ▼" : ""}</button></th>)}
              <th className="num" aria-sort={sort.key === "fee" ? "ascending" : undefined}><button type="button" className={`fd-th${sort.key === "fee" ? " on" : ""}`}
                onClick={() => changeSort({ ...sort, key: "fee" })}>Phí quản lý{sort.key === "fee" ? " ▲" : ""}</button></th>
              <th className="num" aria-sort={sort.key === "score" ? "descending" : undefined}><button type="button" className={`fd-th${sort.key === "score" ? " on" : ""}`}
                onClick={() => changeSort({ ...sort, key: "score" })}>Điểm{sort.key === "score" ? " ▼" : ""}</button></th><th>1 năm so với gửi tiết kiệm</th></tr></thead>
            <tbody>{shown.map((f, i) => { const first = i === 0 || shown[i - 1].kind !== f.kind;
              return [kind === "all" && first ? <tr key={`k-${f.kind}`} className="fd-kindrow"><th colSpan={11}>{f.kind ? KIND_LABEL[f.kind] : "Chưa rõ nhóm"}
                ({shown.filter((x) => x.kind === f.kind).length})</th></tr> : null,
              <tr key={f.code} className={f.held ? "fd-held" : undefined}>
              <td data-label="Quỹ"><strong>{f.code}</strong>{ordered.top[f.code] && <> <span className="pill good" title={`Thứ ${ordered.top[f.code]} trong nhóm theo ${SORTS.find((x) => x.id === sort.key)!.label.toLowerCase()}`}>
                Top {ordered.top[f.code]}</span></>}{f.held && <> <span className="pill">Bạn đang giữ</span></>}{isNewFund(f) && <> <span className="pill warn">quỹ mới &lt; 3 năm</span></>}
                <div className="caption">{f.name}{f.manager ? ` · ${f.manager}` : ""}</div></td>
              <td data-label="Nhóm">{f.kind ? KIND_LABEL[f.kind] : "—"}</td>
              <td className="num" data-label="NAV/đơn vị">{formatDecimal(f.nav, 0)}<div className="caption">{day(f.date)}</div></td>
              {PERIODS.map((p) => <td key={p.key} className={`num ${tone(f.returns?.[p.key]) ?? ""}`} data-label={p.label}>{returnText(f.returns?.[p.key])}</td>)}
              <td className="num" data-label="Phí quản lý">{f.fee === null ? "—" : `${formatDecimal(f.fee, 2)}%`}</td>
              {(() => { const s = scoreView(f.score); return <td className="num" data-label="Điểm" title={s.title}><strong>{s.text}</strong>{s.arrow && <span className="caption"> {s.arrow}</span>}</td>; })()}
              <td data-label="So với gửi tiết kiệm">{f.beats_deposit === null ? "—"
                : f.beats_deposit ? <span className="pill good">Cao hơn</span> : <span className="pill bad">Thấp hơn</span>}</td>
            </tr>]; })}</tbody>
          </table>
          <p className="caption">NAV và lợi nhuận theo từng kỳ là số Fmarket công bố (đơn vị phân phối, không phải công ty quản lý quỹ){board.source
            ? `, lấy lúc ${new Date(board.source.fetched_at).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })}` : ""}. Kỳ Fmarket không có số thì để trống.
            VN-Index tính từ giá đóng cửa đã lưu, cùng các kỳ. Điểm (0–100) chỉ chấm phần đo được, xếp hạng trong cùng nhóm: hiệu suất 1 và 3 năm, phí quản lý
            (thấp hơn là tốt), rủi ro (sụt giảm lớn nhất và độ dao động của NAV, khi đã lưu đủ 120 ngày); triển vọng là nhận định nên không chấm. Mũi tên so
            với điểm tháng trước; rê chuột lên điểm để xem điểm từng phần. Top 1–3 là thứ hạng trong nhóm theo cách sắp xếp đang chọn. Quỹ mới thì lợi nhuận ngắn hạn dao động mạnh; so quỹ cùng nhóm với nhau. Lịch sử NAV bắt đầu lưu
            mỗi ngày: hiện có {days} ngày. Không phải khuyến nghị.</p>
        </>}
      </section>
    </>
  );
}
