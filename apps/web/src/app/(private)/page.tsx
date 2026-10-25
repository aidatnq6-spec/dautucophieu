import { OverviewView } from "../../components/overview-view";

export default function OverviewPage() {
  return (
    <>
      <div className="pagehead"><h1>Một góc nhìn rõ ràng sau mỗi phiên.</h1><p className="muted">Kết luận trước, danh mục ngay bên dưới.</p></div>
      <OverviewView />
    </>
  );
}
