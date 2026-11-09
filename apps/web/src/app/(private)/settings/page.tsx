import { SettingsView } from "../../../components/settings-view";
import { SystemHealth } from "../../../components/system-health";

export default function SettingsPage() {
  return (<><div className="pagehead"><h1>Chọn AI và cách nhận bản tin.</h1><p className="muted">Bí mật chỉ nằm ở máy chủ; trang này chỉ hiện trạng thái.</p></div><SettingsView /><SystemHealth /></>);
}
