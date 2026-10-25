import { WatchlistView } from "../../../components/watchlist-view";

export default function WatchlistPage() {
  return (
    <>
      <div className="pagehead"><h1>Các mã đang theo dõi</h1><p className="muted">Giá đóng cửa gần nhất và mức thay đổi, cập nhật theo lịch chạy.</p></div>
      <WatchlistView />
    </>
  );
}
