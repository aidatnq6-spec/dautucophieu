import { YearEnd } from "../../../components/year-end";
import { YearGoals } from "../../../components/year-goals";
import { YearReview } from "../../../components/year-review";

export default function YearPage() {
  return (
    <>
      <div className="pagehead"><h1>Năm tài chính</h1><p className="muted">Việc cuối năm, tổng kết năm và mục tiêu năm sau. Số của bạn chỉ ở trên máy
        này và kho cá nhân, không gửi cho AI.</p></div>
      <YearEnd />
      <YearReview />
      <YearGoals />
    </>
  );
}
