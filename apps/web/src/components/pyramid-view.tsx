"use client";
import { formatRatio, formatVnd } from "../lib/format";

type Buy = { on: string; outlay: string; level: string };
export type PyramidRow = { key: string; symbol: string; start: string; end: string | null; label: "upright" | "inverted" | "mixed" | null;
  reason: string | null; buys: Buy[]; above_share: string | null; largest: Buy | null; mean_above: string | null; mean_below: string | null };
export type PyramidSummary = { counts: { upright: number; inverted: number; mixed: number }; compared: number; mean_above_share: string | null; enough: boolean };
export type Pyramids = { rows: PyramidRow[]; summary: PyramidSummary };

const LABEL = { upright: "Tháp xuôi", inverted: "Tháp ngược", mixed: "Xen kẽ" };
const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const level = (lv: string) => !/[1-9]/.test(lv) ? "lần mua đầu"
  : `giá ${lv.startsWith("-") ? "thấp" : "cao"} hơn lần mua đầu ${formatRatio(lv.replace("-", ""), 1)}`;

export function largestText(r: Pick<PyramidRow, "largest">): string {
  return r.largest ? `${formatVnd(r.largest.outlay)} ngày ${day(r.largest.on)}, ${level(r.largest.level)}` : "—";
}

export function pyramidSummary(s: PyramidSummary): string {
  if (s.compared === 0) return "Chưa có đợt nào so được.";
  const head = `${s.compared} đợt so được: ${s.counts.upright} tháp xuôi, ${s.counts.inverted} tháp ngược, ${s.counts.mixed} xen kẽ.`;
  return `${head} ${s.enough && s.mean_above_share ? `Bình quân ${formatRatio(s.mean_above_share, 1)} tiền của một đợt bỏ vào ở giá cao hơn lần mua đầu.`
    : "Chưa đủ 5 đợt để tính bình quân."}`;
}

/** Soi hình tháp khi mua thêm, inside Hậu kiểm: where the money of the later buys went against the first buy's (adjusted) price. */
export function PyramidView({ data }: { data: Pyramids }) {
  return <>
    <h3>Hình tháp khi mua thêm</h3>
    <p className="caption">Mỗi đợt nắm có từ 2 lần mua: tiền bỏ ra mỗi lần (gồm phí, thuế) và giá đóng cửa đã điều chỉnh ngày mua so với ngày mua đầu, nên cổ
      phiếu thưởng hay chia tách giữa hai lần mua không làm sai phép so. Tháp xuôi: lần mua nhiều tiền nhất ở giá thấp nhất của đợt. Tháp ngược: lần mua
      nhiều tiền nhất ở giá cao nhất, cao hơn lần mua đầu. Còn lại là xen kẽ. Chỉ mô tả hình dạng, không chấm điểm.</p>
    <p>{pyramidSummary(data.summary)}</p>
    {data.rows.length > 0 && <div className="tablewrap"><table aria-label="Hình tháp khi mua thêm">
      <thead><tr><th>Đợt</th><th>Hình</th><th className="num">Tiền ở giá cao hơn lần đầu</th><th>Lần mua nhiều tiền nhất</th><th>Bình quân mỗi lần</th></tr></thead>
      <tbody>{data.rows.map((r) => <tr key={r.key}>
        <td data-label="Đợt"><strong>{r.symbol}</strong><div className="caption">{day(r.start)} → {r.end ? day(r.end) : "đang nắm"} · {r.buys.length || "—"} lần mua</div></td>
        <td data-label="Hình">{r.label ? <span className="pill">{LABEL[r.label]}</span>
          : <span className="muted">chưa so được: {r.reason}</span>}</td>
        <td data-label="Tiền ở giá cao hơn lần đầu" className="num">{r.above_share ? formatRatio(r.above_share, 1) : "—"}</td>
        <td data-label="Lần mua nhiều tiền nhất">{largestText(r)}</td>
        <td data-label="Bình quân mỗi lần">{r.label ? <>trên giá đầu {r.mean_above ? formatVnd(r.mean_above) : "—"}
          <div className="caption">bằng hoặc dưới giá đầu {r.mean_below ? formatVnd(r.mean_below) : "—"}</div></> : "—"}</td>
      </tr>)}</tbody>
    </table></div>}
  </>;
}
