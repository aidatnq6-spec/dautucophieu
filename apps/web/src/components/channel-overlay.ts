import type { Channels, T } from "./bar-channels";

/** One read-only line on the weekly price pane. style: 0 solid, 1 dotted, 2 dashed (lightweight-charts LineStyle). */
export type Segment = { key: string; color: string; width: 1 | 2 | 3; style: 0 | 1 | 2; points: { t: T; p: number }[] };
export type Marker = { time: T; position: "belowBar" | "aboveBar"; shape: "arrowUp" | "arrowDown"; color: string; text: string };

export const OVERLAY = { channel: "var(--overlay-channel)", zone: "var(--overlay-zone)", broken: "var(--overlay-broken)" };

/** Lines up to the last finished bar only: channels from their first joining point, zones at their low. Never into the future. */
export function channelSegments(d: Channels): Segment[] {
  const last = d.last_bar;
  if (last === null) return [];
  const out: Segment[] = d.bases.map((b, i) => ({ key: `zone-${i}`, color: OVERLAY.zone, width: 3, style: 0,
    points: [{ t: b.zone_from, p: Number(b.low) }, { t: b.zone_to, p: Number(b.low) }] }));
  for (const c of d.channels) {
    if (c.from.date >= last) continue;
    const width = Number(c.upper_now) - Number(c.lower_now);
    const final = c.kind === "final";
    const style: 0 | 2 = c.kind.startsWith("accel") ? 2 : 0;
    const from = (k: number) => ({ t: c.from.date, p: Number(c.from.price) + k * width });
    out.push({ key: `${c.kind}-lower`, color: OVERLAY.channel, width: final ? 3 : 2, style, points: [from(0), { t: last, p: Number(c.lower_now) }] });
    out.push({ key: `${c.kind}-upper`, color: OVERLAY.channel, width: 1, style, points: [from(1), { t: last, p: Number(c.upper_now) }] });
    if (final) out.push({ key: "final-double", color: OVERLAY.channel, width: 1, style: 1, points: [from(2), { t: last, p: Number(c.double_now) }] });
  }
  return out;
}

export function channelMarkers(d: Channels): Marker[] {
  const zones: Marker[] = d.bases.map((b, i) => ({ time: b.low_date, position: "belowBar", shape: "arrowUp", color: OVERLAY.zone,
    text: `d${i + 1}${i === d.zero ? " · 0" : ""}` }));
  const breaks: Marker[] = d.breaks.map((b) => ({ time: b.date, position: "aboveBar", shape: "arrowDown", color: OVERLAY.broken, text: "phá kênh" }));
  return [...zones, ...breaks].sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
}
