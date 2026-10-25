export type Evidence = { evidence_id: string; title: string; kind: string; source_url: string; published: string };

export function SourceEvidence({ items }: { items: Evidence[] }) {
  return (
    <section className="surface" aria-labelledby="evidence-title">
      <h2 id="evidence-title">Nguồn và bằng chứng</h2>
      {items.length === 0 ? <p className="notice">Chưa có tài liệu nguồn cho mã này; không đưa ra nhận định dựa trên dữ liệu thiếu.</p> : (
        <ul>{items.map((e) => (
          <li key={e.evidence_id} id={e.evidence_id}>
            <strong>{e.title}</strong> · {e.kind} · công bố {e.published} · <code>{e.evidence_id}</code>{" "}
            <a href={e.source_url} rel="noopener noreferrer" target="_blank">Mở tài liệu gốc</a>
          </li>))}</ul>
      )}
    </section>
  );
}
