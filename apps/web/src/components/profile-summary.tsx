"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { EquityBudget } from "./equity-budget";
import { WealthCheck } from "./wealth-check";
import { LifestyleInflation } from "./lifestyle";
import { Intangibles } from "./intangibles";
import { Contributions } from "./contributions";
import { PassiveIncome } from "./passive-income";
import { type Assessment } from "./profile-form";
import { RiskSection } from "./risk-section";

type ProfileView = { version: number; assessment: Assessment; confirmed_at: string; freshness: { status: string; allows_new_recommendations: boolean } };
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
      {/* The confirmed profile still gates new recommendations; it needs the owner only when missing or due, so it is shown only then. */}
      {(!p || p.freshness.status !== "current") && <section className="surface" aria-label="Vốn có thể đầu tư">
        <div className="row"><h2>Hồ sơ tài chính</h2><Link href="/onboarding">Cập nhật hồ sơ</Link></div>
        {!p ? <p className="notice">Chưa có hồ sơ tài chính đã xác nhận.</p>
          : <p className="notice">{FRESHNESS[p.freshness.status]} (xác nhận {new Date(p.confirmed_at).toLocaleDateString("vi-VN")}).
            {!p.freshness.allows_new_recommendations && " Gợi ý mua mới tạm dừng cho tới khi bạn xác nhận lại."}</p>}
      </section>}
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
