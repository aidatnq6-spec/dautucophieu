import { EventsView } from "../../../components/events-view";

export default function EventsPage() {
  return (
    <>
      <div className="pagehead"><h1>Lịch sự kiện</h1><p className="muted">Cổ tức, phát hành, đại hội cổ đông của các mã đang theo dõi.</p></div>
      <EventsView />
    </>
  );
}
