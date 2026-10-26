import { JournalView } from "../../../components/journal-view";

export default function JournalPage() {
  return (
    <>
      <div className="pagehead"><h1>Nhật ký</h1><p className="muted">Lý do và cảm xúc lúc ra quyết định, để tự xem lại khi giá đã đi xa.</p></div>
      <JournalView />
    </>
  );
}
