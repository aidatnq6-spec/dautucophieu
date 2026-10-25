import { ReportsList } from "../../../components/reports-list";

export default function ReportsPage() {
  return (
    <>
      <div className="pagehead"><h1>Điều gì đã thay đổi sau phiên?</h1><p className="muted">Ngày phiên và ngày chạy được ghi riêng; bản tin chỉ phát hành một lần cho cùng dữ liệu đầu vào.</p></div>
      <ReportsList />
    </>
  );
}
