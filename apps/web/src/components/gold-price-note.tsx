import { formatRatio } from "../lib/format";

export type GoldMove = { basis: "kind" | "world"; from: string; to: string; days: number; change: string; strong: boolean };
export type GoldPriceMoves = { threshold: string; world: GoldMove | null; kinds: Record<string, GoldMove> };

const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** Nhắc "đừng hành động theo giá": a 30-day move of 10% or more, by the kind's own buying price or the world price standing in. */
export function priceNote(move: GoldMove | null | undefined, kind: string | null): string | null {
  if (!move || !move.strong) return null;
  const price = move.basis === "kind" ? `${kind} (giá mua vào Phú Quý)`
    : kind ? `vàng thế giới (PAXG-USD; giá ${kind} chưa đủ 30 ngày)` : "vàng thế giới (PAXG-USD)";
  const word = move.change.startsWith("-") ? "giảm" : "tăng";
  const size = formatRatio(move.change.replace(/^-/, ""));
  return `Giá ${price} đã ${word} ${size} trong ${move.days} ngày (${dmy(move.from)} → ${dmy(move.to)}). `
    + "Mua bán vàng theo tỷ trọng của Tháp tài sản (10–15%), không theo giá.";
}

/** The move for a kind (null: a row without a kind, valued at cost): its own, else the world price standing in. */
export function moveFor(moves: GoldPriceMoves | undefined, kind: string | null): GoldMove | null {
  if (!moves) return null;
  return (kind ? moves.kinds[kind] : null) ?? moves.world;
}

/** The notes for these kinds, one per distinct note; nothing below the threshold. */
export function GoldPriceNotes({ moves, kinds }: { moves: GoldPriceMoves | undefined; kinds: (string | null)[] }) {
  const notes = [...new Set([...new Set(kinds)].map((k) => priceNote(moveFor(moves, k), k)).filter((n): n is string => n !== null))];
  if (!notes.length) return null;
  return <div role="note" aria-label="Nhắc về giá vàng" className="notice">{notes.map((n) => <p key={n}>{n}</p>)}</div>;
}
