import { Suspense } from "react";
import { ProfileSummary } from "../../../components/profile-summary";

export default function ProfilePage() {
  return (
    <>
      <div className="pagehead"><h1>Hồ sơ & rủi ro</h1><p className="muted">Mẫu số phân bổ và nhóm rủi ro đang dùng.</p></div>
      <Suspense fallback={<p className="muted fx-loading" role="status">Đang tải…</p>}><ProfileSummary /></Suspense>
    </>
  );
}
