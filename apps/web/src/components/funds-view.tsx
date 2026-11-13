"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

export type Kind = "STOCK" | "BALANCED" | "BOND";
type Returns = { ytd: string | null; m1: string | null; m3: string | null; m6: string | null; m12: string | null; m36: string | null; m60: string | null; annual36: string | null };
type Fund = { code: string; name: string; kind: Kind | null; manager: string | null; fee: string | null; nav: string; date: string;
  returns: Returns | null; held: boolean; beats_deposit: boolean | null };
type Group = { kind: Kind | "unknown"; value: string; share: string; funds: string[] };
type Mine = { groups: Group[]; total: string; fund_count: number; at_cost: string[]; notes: ("fewer_than_3" | "single_kind")[] };
type Board = { funds: Fund[]; counts: Record<Kind, number>;
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

export function FundsView() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<Kind | "all">("all");
  useEffect(() => { api<Board>("funds").then(setBoard, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!board) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const shown = board.funds.filter((f) => kind === "all" || f.kind === kind);
  const vn = board.benchmark.vnindex, deposit = board.benchmark.deposit_12m;
  const days = Math.max(0, ...Object.values(board.history_days));
  return (
    <>
      <MineSection mine={board.mine} />
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
          <table className="fv-table" aria-label="Danh sách quỹ mở">
            <thead><tr><th>Quỹ</th><th>Nhóm</th><th className="num">NAV/đơn vị</th>{PERIODS.map((p) => <th key={p.key} className="num">{p.label}</th>)}
              <th className="num">Phí quản lý</th><th>1 năm so với gửi tiết kiệm</th></tr></thead>
            <tbody>{shown.map((f) => <tr key={f.code} className={f.held ? "fd-held" : undefined}>
              <td data-label="Quỹ"><strong>{f.code}</strong>{f.held && <> <span className="pill">Bạn đang giữ</span></>}
                <div className="caption">{f.name}{f.manager ? ` · ${f.manager}` : ""}</div></td>
              <td data-label="Nhóm">{f.kind ? KIND_LABEL[f.kind] : "—"}</td>
              <td className="num" data-label="NAV/đơn vị">{formatDecimal(f.nav, 0)}<div className="caption">{day(f.date)}</div></td>
              {PERIODS.map((p) => <td key={p.key} className={`num ${tone(f.returns?.[p.key]) ?? ""}`} data-label={p.label}>{returnText(f.returns?.[p.key])}</td>)}
              <td className="num" data-label="Phí quản lý">{f.fee === null ? "—" : `${formatDecimal(f.fee, 2)}%`}</td>
              <td data-label="So với gửi tiết kiệm">{f.beats_deposit === null ? "—"
                : f.beats_deposit ? <span className="pill good">Cao hơn</span> : <span className="pill bad">Thấp hơn</span>}</td>
            </tr>)}</tbody>
          </table>
          <p className="caption">NAV và lợi nhuận theo từng kỳ là số Fmarket công bố (đơn vị phân phối, không phải công ty quản lý quỹ){board.source
            ? `, lấy lúc ${new Date(board.source.fetched_at).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })}` : ""}. Kỳ Fmarket không có số thì để trống.
            VN-Index tính từ giá đóng cửa đã lưu, cùng các kỳ. Quỹ mới thì lợi nhuận ngắn hạn dao động mạnh; so quỹ cùng nhóm với nhau. Lịch sử NAV bắt đầu lưu
            mỗi ngày: hiện có {days} ngày. Không phải khuyến nghị.</p>
        </>}
      </section>
    </>
  );
}
