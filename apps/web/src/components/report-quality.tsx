import { Check, CircleHelp, X } from "lucide-react";

type Criterion = { id: string; label: string; passed: boolean | null; detail: string };
type Sign = { id: string; label: string; flag: boolean | null; detail: string; rule?: string };
// kind: Piotroski's F-Score for most tickers; "health" for banks, securities firms and insurers (sector ratios, no level).
export type Quality = { applicable: boolean; reason: string | null; signs: Sign[]; note?: string | null;
  f_score: { kind?: "f_score" | "health"; title?: string; year: string; score: number; evaluated: number; level: "strong" | "medium" | "weak" | null;
    criteria: Criterion[] } | null };

const LEVEL = { strong: { label: "mạnh", tone: "good" }, medium: { label: "trung bình", tone: "" }, weak: { label: "yếu", tone: "bad" } } as const;

/** Score in a table cell: F-Score or the sector health score over evaluated criteria, the level when there is one, or why there is none. */
export function FScoreCell({ q }: { q: Quality | undefined }) {
  if (!q) return <>—</>;
  if (!q.applicable) return <span className="caption">Không áp dụng</span>;
  const f = q.f_score;
  if (!f) return <span className="caption">Chưa có số liệu</span>;
  const flags = q.signs.filter((s) => s.flag).length;
  return <>
    {f.score}/{f.evaluated}{f.level && <> <span className={`pill ${LEVEL[f.level].tone}`}>{LEVEL[f.level].label}</span></>}
    <div className="caption">{f.kind === "health" ? "sức khỏe ngành" : "F-Score"}</div>
    {flags > 0 && <div className="caption">{flags} dấu hiệu cần xem kỹ</div>}
  </>;
}

const mark = (v: boolean | null, good: boolean) => v === null
  ? <CircleHelp size={14} aria-label="không đánh giá được" className="muted" />
  : v === good ? <Check size={14} aria-label="đạt" className="positive" /> : <X size={14} aria-label="không đạt" className="negative" />;

/** The criteria with their figures, then (F-Score only) the warning signs with their numbers and the app's own rule. */
export function QualityList({ symbol, q }: { symbol: string; q: Quality | undefined }) {
  if (!q) return null;
  const f = q.f_score;
  const health = f?.kind === "health";
  return (
    <section aria-label={`Chất lượng báo cáo ${symbol}`}>
      <h3>Chất lượng báo cáo</h3>
      {!f ? <p className="muted">{q.reason}</p> : <>
        <p><strong>{health ? `${f.title} ${f.year}` : `F-Score năm ${f.year}`}: {f.score}/{f.evaluated} tiêu chí đánh giá được</strong>
          {f.level ? <> · <span className={`pill ${LEVEL[f.level].tone}`}>{LEVEL[f.level].label}</span></>
            : <span className="caption"> · cần ít nhất 7/9 số tiêu chí đánh giá được mới xếp mức</span>}</p>
        <ul className="quality-list">{f.criteria.map((c) => <li key={c.id}>{mark(c.passed, true)} <strong>{c.label}</strong>
          <span className="caption"> — {c.detail}</span></li>)}</ul>
        {q.signs.length > 0 && <>
          <h4>Dấu hiệu cần xem kỹ</h4>
          {q.note && <p className="notice">{q.note}</p>}
          <ul className="quality-list">{q.signs.map((s) => <li key={s.id}>{mark(s.flag, false)} <strong>{s.label}</strong>
            {s.flag && <> <span className="pill warn">cần xem kỹ</span></>}
            <span className="caption"> — {s.detail}{s.rule ? ` (quy tắc: ${s.rule})` : ""}</span></li>)}</ul>
        </>}
        {health
          ? <p className="caption">F-Score của Piotroski không dùng được cho ngân hàng, chứng khoán, bảo hiểm. Điểm sức khỏe là bộ tiêu chí của ứng dụng từ chỉ số ngành
            VNDirect công bố, so quý gần nhất với cùng quý năm trước. Mức xếp theo quy tắc của ứng dụng, quy đổi mốc Piotroski theo số tiêu chí: mạnh khi trượt
            nhiều nhất 1 tiêu chí, yếu khi đạt không quá 2/9 số tiêu chí. Không phải lời khuyên mua bán.</p>
          : <p className="caption">F-Score (Piotroski): 9 tiêu chí so năm gần nhất với năm trước; 8–9 mạnh, 0–2 yếu. Dấu hiệu là quy tắc của ứng dụng,
            chỉ cho thấy điểm bất thường cần đọc kỹ báo cáo, không kết luận gian lận và không phải lời khuyên mua bán. Nguồn: Vnstock (gói miễn phí), không có khấu
            hao nên chưa tính M-Score.</p>}
      </>}
    </section>
  );
}
