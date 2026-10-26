"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BookOpenText, Briefcase, ChartLine, Eye, Globe, House, Newspaper, Scale, Settings, UserRound } from "lucide-react";

const LINKS = [
  { href: "/", label: "Tổng quan", icon: House },
  { href: "/portfolio", label: "Danh mục & Giao dịch", icon: Briefcase },
  { href: "/macro", label: "Vĩ mô", icon: Globe },
  { href: "/insights", label: "Nhận định", icon: Newspaper },
  { href: "/trend", label: "Xu hướng", icon: Activity },
  { href: "/market", label: "Thị trường & Ngành", icon: ChartLine },
  { href: "/watchlist", label: "Theo dõi", icon: Eye },
  { href: "/fair-value", label: "Định giá", icon: Scale },
  { href: "/reports", label: "Bản tin sau phiên", icon: BookOpenText },
  { href: "/profile", label: "Hồ sơ & rủi ro", icon: UserRound },
  { href: "/settings", label: "Cài đặt", icon: Settings },
];

export function AppNav() {
  const path = usePathname();
  return (
    <nav className="nav" aria-label="Điều hướng chính">
      {LINKS.map(({ href, label, icon: Icon }) => (
        <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>
          <Icon size={18} aria-hidden="true" />{label}
        </Link>
      ))}
    </nav>
  );
}
