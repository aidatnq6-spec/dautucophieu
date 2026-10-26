import { FairValueView } from "../../../components/fair-value-view";

export default function FairValuePage() {
  return (
    <>
      <div className="pagehead"><h1>Giá hiện tại rẻ hay đắt?</h1><p className="muted">Nhiều phương án định giá theo ngành cho các mã đang theo dõi, để tham khảo.</p></div>
      <FairValueView />
    </>
  );
}
