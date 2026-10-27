"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";
import { EquityBudget } from "./equity-budget";
import { WealthCheck } from "./wealth-check";
import { LifestyleInflation } from "./lifestyle";
import { Intangibles } from "./intangibles";
import { Contributions } from "./contributions";
import { PassiveIncome } from "./passive-income";
import { BreakdownTable, STATUS_LABEL, WARNING_LABEL, refNames, type Assessment } from "./profile-form";
import { RiskSection } from "./risk-section";

type ProfileView = { version: number; assessment: Assessment; confirmed_at: string;
  profile: { assets: { asset_id: string; kind: string }[]; goals: { goal_id: string; due_date: string }[] }; freshness: { status: string; allows_new_recommendations: boolean } };
const FRESHNESS: Record<string, string> = { current: "Còn hiệu lực", refresh_soon: "Sắp đến hạn rà soát tháng",
  reconfirm_required: "Cần xác nhận lại trước khuyến nghị mới" };

function useRecord<T>(path: string) {
  const [value, setValue] = useState<T | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<T>(path).then(setValue).catch((e) => {
      if (e instanceof ApiError && e.failure.status === 404) setValue(null);
      else setError(e instanceof ApiError ? e.failure.message : "Không tải được dữ liệu.");
    });
  }, [path]);
  return { value, error };
}

export function ProfileSummary() {
  const profile = useRecord<ProfileView>("profile");
  const [riskChanges, setRiskChanges] = useState(0);
  const [wealthSaves, setWealthSaves] = useState(0);
  const [intangibleChanges, setIntangibleChanges] = useState(0);
  if (profile.error) return <p className="errors" role="alert">{profile.error}</p>;
  if (profile.value === undefined) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const p = profile.value;
  return (
    <>
      <section className="surface" aria-label="Vốn có thể đầu tư">
        <div className="row"><h2>Vốn có thể đầu tư</h2><Link href="/onboarding">Cập nhật hồ sơ</Link></div>
        {!p ? <p className="notice">Chưa có hồ sơ tài chính đã xác nhận.</p> : (<>
          <p><span className="pill">{STATUS_LABEL[p.assessment.status]}</span>{" "}
            <span className={`pill ${p.freshness.allows_new_recommendations ? "good" : "warn"}`}>{FRESHNESS[p.freshness.status]}</span>{" "}
            Hồ sơ xác nhận {new Date(p.confirmed_at).toLocaleDateString("vi-VN")} · <strong>Vốn có thể đầu tư lúc xác nhận: {formatVnd(p.assessment.net)}</strong></p>
          <p className="caption">Số chốt tại lúc xác nhận hồ sơ (phiên bản {p.version}), dùng để biết hồ sơ còn hiệu lực. Số mới nhất xem ở Tháp tài sản bên dưới.</p>
          {p.assessment.warnings.map((w) => <p key={w.code} className="notice">{WARNING_LABEL[w.code] ?? w.code}: {formatVnd(w.amount)}</p>)}
          <details className="pc-details">
            <summary>Xem chi tiết</summary>
            <BreakdownTable assessment={p.assessment} names={refNames(p.profile?.assets ?? [], p.profile?.goals ?? [])} />
          </details>
        </>)}
      </section>
      <RiskSection onChanged={() => setRiskChanges((n) => n + 1)} />
      <WealthCheck onSaved={() => setWealthSaves((n) => n + 1)} />
      <LifestyleInflation refresh={wealthSaves} />
      <Contributions />
      <PassiveIncome />
      <Intangibles onChanged={() => setIntangibleChanges((n) => n + 1)} />
      <EquityBudget key={`${riskChanges}-${intangibleChanges}`} />
    </>
  );
}
