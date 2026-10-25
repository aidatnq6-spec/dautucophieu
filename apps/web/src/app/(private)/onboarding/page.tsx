import { OnboardingFlow } from "../../../components/onboarding-flow";

export default function OnboardingPage() {
  return (
    <>
      <div className="pagehead"><h1>Thiết lập ban đầu</h1>
        <p className="muted">Hồ sơ → khảo sát → sổ giao dịch. Thiếu hồ sơ hoặc khảo sát thì chỉ có báo cáo tài sản, chưa có khuyến nghị cá nhân hóa.</p></div>
      <OnboardingFlow />
    </>
  );
}
