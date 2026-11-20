import { formatDecimal, formatRatio, formatVnd } from "../lib/format";

export type Drawdown = { since: string | null; peak: string | null; peak_date: string | null; latest: string | null; latest_date: string | null;
  change: string | null; stale: boolean; missing: "no_data" | null };
export type PassThrough = { missing: "no_data" | "not_enough_history" | null; since: string | null; ready_on: string | null; days: number | null;
  from: string | null; to: string | null; sjc_from: string | null; sjc_to: string | null; world_from: string | null; world_to: string | null;
  sjc_change: string | null; world_change: string | null };
export type GoldMovesData = { world: Drawdown; sjc: Drawdown; pass_through: PassThrough };

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** The 30-day line: both moves over their dates, or why there is none yet. */
export function passThroughText(p: PassThrough): string {
  if (p.missing === "no_data") return "Chưa có ngày nào có cả giá SJC và giá thế giới quy ra đồng.";
  if (p.missing === "not_enough_history")
    return `Chưa đủ 30 ngày số liệu: giá SJC và giá thế giới cùng có từ ${dmy(p.since!)}, nên có số từ khoảng ${dmy(p.ready_on!)}.`;
  return `Từ ${dmy(p.from!)} đến ${dmy(p.to!)} (${p.days} ngày): vàng miếng SJC ${formatRatio(p.sjc_change)}, giá thế giới quy ra đồng ${formatRatio(p.world_change)}.`;
}

function Row({ name, basis, d, money }: { name: string; basis: string; d: Drawdown; money: (v: string) => string }) {
  if (d.missing) return <tr><th scope="row">{name}<div className="caption">{basis}</div></th><td colSpan={3} className="muted">Chưa có số liệu.</td></tr>;
  return (
    <tr>
      <th scope="row">{name}<div className="caption">{basis}, từ {dmy(d.since!)}</div></th>
      <td data-label="Đỉnh">{money(d.peak!)}<div className="caption">{dmy(d.peak_date!)}</div></td>
      <td data-label="Mới nhất">{money(d.latest!)}<div className="caption">{dmy(d.latest_date!)}{d.stale && <> · <span className="negative">số liệu cũ</span></>}</div></td>
      <td data-label="So với đỉnh"><strong>{formatRatio(d.change)}</strong></td>
    </tr>
  );
}

/** Sụt từ đỉnh and the 30-day pass-through, inside the SJC gap section. */
export function GoldMoves({ moves }: { moves: GoldMovesData }) {
  return (
    <div aria-label="Vàng: sụt từ đỉnh và độ truyền giá" role="group">
      <h3>Sụt từ đỉnh</h3>
      <table className="table">
        <thead><tr><th scope="col">Loại</th><th scope="col">Đỉnh</th><th scope="col">Mới nhất</th><th scope="col">So với đỉnh</th></tr></thead>
        <tbody>
          <Row name="Vàng thế giới" basis="PAXG-USD (Coinbase), gần đúng giá vàng, USD/oz" d={moves.world} money={(v) => formatDecimal(v, 2)} />
          <Row name="Vàng miếng SJC" basis="giá mua vào Phú Quý, đồng/chỉ" d={moves.sjc} money={(v) => formatVnd(v)} />
        </tbody>
      </table>
      <p className="caption">Đỉnh là giá cao nhất trong số liệu đã lưu, tính từ ngày ghi bên cạnh; không phải đỉnh mọi thời.</p>
      <h3>Độ truyền giá trong 30 ngày</h3>
      <p>{passThroughText(moves.pass_through)}</p>
      <p className="caption">Giá thế giới quy ra đồng/chỉ như chênh lệch ở trên (XAU/USD gold-api.com × tỷ giá bán Vietcombank); SJC theo giá mua vào
        Phú Quý. Chỉ so những ngày có cả hai giá.</p>
    </div>
  );
}
