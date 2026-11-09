import { ThemeToggle } from "../../../components/theme-toggle";
import { SettingsView } from "../../../components/settings-view";
import { SystemHealth } from "../../../components/system-health";

export default function SettingsPage() {
  return (<><div className="pagehead"><h1>Cài đặt</h1><p className="muted">Phí giao dịch, định giá, Telegram, AI và tình trạng hệ thống. Bí mật chỉ nằm ở máy chủ; trang này chỉ hiện trạng thái.</p></div><section className="surface theme-mobile"><h3>Giao diện</h3><ThemeToggle /></section><SettingsView /><SystemHealth /></>);
}
