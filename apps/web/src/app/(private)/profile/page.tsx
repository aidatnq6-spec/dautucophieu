import { ProfileSummary } from "../../../components/profile-summary";

export default function ProfilePage() {
  return (
    <>
      <div className="pagehead"><h1>Hồ sơ & rủi ro</h1><p className="muted">Mẫu số phân bổ và nhóm rủi ro đang dùng.</p></div>
      <ProfileSummary />
    </>
  );
}
