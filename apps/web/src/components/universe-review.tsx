"use client";
import { useCallback, useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { ApiError, api, requestId, type ApiFailure } from "../lib/api";
import { FormErrors } from "./form-errors";

type Active = { version: number; status: string; members: string[]; gaps: string[]; policy_version: string; as_of: string };
type Proposal = { proposal: { proposal_id: string; base_version: number; members: string[]; added: string[]; removed: string[];
  results: { entity_id: string; reasons: string[] }[]; industry_counts: Record<string, number>; policy_version: string }; decision: string };
const GAP: Record<string, string> = { target_50: "Chưa đủ 50 mã đạt kiểm tra", policy_unconfirmed: "Ngưỡng chính sách chưa được bạn xác nhận" };

export function UniverseReview() {
  const [active, setActive] = useState<{ version: number; active: Active | null } | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [failure, setFailure] = useState<ApiFailure | null>(null);
  const load = useCallback(() => Promise.all([api<{ version: number; active: Active | null }>("universe"), api<{ proposals: Proposal[] }>("universe/proposals")])
    .then(([a, p]) => { setActive(a); setProposals(p.proposals); }, (e) => { if (e instanceof ApiError) setFailure(e.failure); }), []);
  useEffect(() => { void load(); }, [load]);

  async function decide(id: string, decision: "approve" | "reject") {
    setFailure(null);
    try { await api(`universe/proposals/${id}/${decision}`, { method: "POST", body: { request_id: requestId() } }); await load(); }
    catch (e) { if (e instanceof ApiError) setFailure(e.failure); }
  }

  if (!active) return <><FormErrors failure={failure} /><p className="muted fx-loading" role="status">Đang tải…</p></>;
  const a = active.active;
  return (
    <>
      <FormErrors failure={failure} />
      <section className="surface" data-testid="active-universe">
        <h2>Danh sách đang áp dụng</h2>
        {!a ? <p>Chưa có danh sách được duyệt.</p> : (<>
          <p><span className={`pill ${a.status === "complete" ? "good" : "warn"}`}>{a.status === "complete" ? "Đủ 50 mã" : "Chưa đầy đủ"}</span> Phiên bản {active.version} · {a.members.length} mã · chính sách {a.policy_version}</p>
          <ul>{a.gaps.map((g) => <li key={g}>{GAP[g] ?? g}</li>)}</ul>
          {a.members.length > 0 && <p className="wrap">{a.members.join(", ")}</p>}
        </>)}
        <p className="caption">Bằng chứng gửi qua giao diện không được coi là kiểm tra nguồn đã xác minh; danh sách đủ 50 chỉ kích hoạt khi mọi mã đạt kiểm tra nguồn được phép dùng.</p>
      </section>
      <section className="surface">
        <h2>Đề xuất thay đổi</h2>
        {proposals.length === 0 && <p className="muted">Chưa có đề xuất.</p>}
        {proposals.map(({ proposal: p, decision }) => (
          <article key={p.proposal_id} className="surface" data-testid={`proposal-${p.proposal_id}`}>
            <div className="row"><strong>Đề xuất {p.proposal_id}</strong><span className="pill">{{ pending: "Chờ duyệt", approved: "Đã duyệt", rejected: "Đã từ chối" }[decision] ?? decision}</span></div>
            <p>Thêm: {p.added.join(", ") || "không"} · Loại: {p.removed.join(", ") || "không"} · Dựa trên phiên bản {p.base_version}</p>
            <ul>{p.results.filter((r) => r.reasons.length).map((r) => <li key={r.entity_id}>{r.entity_id}: {r.reasons.join(", ")}</li>)}</ul>
            {decision === "pending" && <div className="actions">
              <button className="btn primary" onClick={() => void decide(p.proposal_id, "approve")}><Check size={16} aria-hidden="true" />Duyệt đề xuất {p.proposal_id}</button>
              <button className="btn" onClick={() => void decide(p.proposal_id, "reject")}><X size={16} aria-hidden="true" />Từ chối đề xuất {p.proposal_id}</button>
            </div>}
          </article>
        ))}
      </section>
    </>
  );
}
