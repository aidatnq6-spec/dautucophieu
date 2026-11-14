/** Trợ lý: understands a typed question by keywords (no AI, nothing leaves the machine) and knows where every page is. */

export type Intent =
  | { kind: "today" } | { kind: "portfolio" } | { kind: "money_in" } | { kind: "theses" } | { kind: "report" } | { kind: "health" }
  | { kind: "stock"; symbol: string; focus: "price" | "valuation" | "thesis" | "events" }
  | { kind: "go"; matches: Destination[] } | { kind: "unknown" };

export type Destination = { label: string; href: string; keys: string[] };

/** Every page and the parts people look for, with the words that lead to them (written without accents). */
export const DESTINATIONS: Destination[] = [
  { label: "Tổng quan", href: "/", keys: ["tong quan", "trang chu", "dashboard"] },
  { label: "Danh mục & Giao dịch", href: "/portfolio", keys: ["danh muc", "giao dich", "so lenh", "lenh mua", "lenh ban"] },
  { label: "Vì sao tài sản tháng này thay đổi (thác nước)", href: "/portfolio", keys: ["thac nuoc", "tai san thay doi", "vi sao tai san"] },
  { label: "Bản đồ danh mục", href: "/portfolio", keys: ["ban do danh muc", "ban do", "treemap"] },
  { label: "Lịch lãi/lỗ hằng ngày", href: "/portfolio", keys: ["lich lai lo", "lai lo hang ngay", "lich nhiet"] },
  { label: "Kế hoạch giải ngân", href: "/portfolio", keys: ["giai ngan", "ke hoach mua", "dot mua"] },
  { label: "Luận điểm đầu tư", href: "/portfolio", keys: ["luan diem"] },
  { label: "Bản tổng kết tháng để in", href: "/monthly", keys: ["tong ket thang", "bao cao thang", "in thang"] },
  { label: "Hồ sơ & rủi ro", href: "/profile", keys: ["ho so", "rui ro", "khau vi"] },
  { label: "Sổ tài sản, tháp tài sản", href: "/profile?tab=tai-san", keys: ["so tai san", "thap tai san", "so tiet kiem", "tien gui", "vang", "trai phieu"] },
  { label: "Radar sức khỏe tài chính, dòng tiền thụ động", href: "/profile?tab=dong-tien", keys: ["radar", "suc khoe tai chinh", "dong tien thu dong", "thu chi", "tiet kiem"] },
  { label: "Kế hoạch: góp vốn đều, tích sản", href: "/profile?tab=ke-hoach", keys: ["gop von", "tich san", "tien moi"] },
  { label: "Vĩ mô", href: "/macro", keys: ["vi mo", "lai suat", "cpi", "lam phat", "ty gia", "gia dau"] },
  { label: "Thị trường trong phiên", href: "/market", keys: ["thi truong", "trong phien", "vnindex", "vn-index", "do rong"] },
  { label: "Ngành theo quý", href: "/sectors", keys: ["nganh"] },
  { label: "Xu hướng", href: "/trend", keys: ["xu huong", "macd", "rsi", "bieu do ky thuat", "ky thuat"] },
  { label: "Theo dõi, bong bóng góc phần tư", href: "/watchlist", keys: ["theo doi", "bong bong", "goc phan tu", "bo loc"] },
  { label: "Định giá", href: "/fair-value", keys: ["dinh gia", "gia tri hop ly", "re dat"] },
  { label: "Mùa báo cáo", href: "/earnings", keys: ["mua bao cao", "bctc", "ket qua kinh doanh"] },
  { label: "Lịch sự kiện", href: "/events", keys: ["lich su kien", "su kien", "co tuc", "dhcd", "dai hoi"] },
  { label: "Quỹ mở", href: "/funds", keys: ["quy mo", "chung chi quy", "nav", "quy"] },
  { label: "Nhận định", href: "/insights", keys: ["nhan dinh", "bao cao ctck", "ctck"] },
  { label: "Bản tin sau phiên", href: "/reports", keys: ["ban tin", "sau phien"] },
  { label: "Tính khoản vay", href: "/loan", keys: ["khoan vay", "vay", "tra gop"] },
  { label: "Nhật ký, quy trình đầu tư", href: "/journal", keys: ["nhat ky", "kanban", "quy trinh"] },
  { label: "Cài đặt", href: "/settings", keys: ["cai dat", "telegram", "thong bao"] },
];

/** Lower case without Vietnamese accents, so "Đáo hạn" and "dao han" match the same words. */
export function plain(text: string): string {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase().replace(/\s+/g, " ").trim();
}

const has = (t: string, words: string[]) => words.some((w) => new RegExp(`(^|[^a-z0-9])${w}([^a-z0-9]|$)`).test(t));
const STOP = new Set(["lai", "lo", "ban", "mua", "co", "tuc", "gia", "thi", "nao", "hom", "nay", "the", "toi", "con", "sap", "ngay", "tin", "von", "quy"]);

/** The ticker a question names: typed in capitals, or a watched ticker in any case unless it is a common Vietnamese word. */
export function findSymbol(text: string, symbols: string[]): string | null {
  const known = new Set(symbols);
  for (const raw of text.split(/[^A-Za-z0-9]+/)) {
    const up = raw.toUpperCase();
    if (!known.has(up)) continue;
    if (raw === up || !STOP.has(raw.toLowerCase())) return up;
  }
  return null;
}

export function parse(text: string, symbols: string[]): Intent {
  const t = plain(text);
  if (!t) return { kind: "unknown" };
  const symbol = findSymbol(text, symbols);
  if (symbol) {
    const focus = has(t, ["dinh gia", "re", "dat", "p/e", "pe", "pb"]) ? "valuation" : has(t, ["luan diem", "kich ban", "chi bao"]) ? "thesis"
      : has(t, ["su kien", "co tuc", "dhcd", "dai hoi"]) ? "events" : "price";
    return { kind: "stock", symbol, focus };
  }
  if (has(t, ["mo", "di toi", "trang", "o dau", "tim"]) || t.split(" ").length <= 3) {
    const go = destinations(t);
    if (go.length && (has(t, ["mo", "di toi", "trang", "o dau", "tim"]) || !intentWords(t))) return { kind: "go", matches: go };
  }
  return intentWords(t) ?? (destinations(t).length ? { kind: "go", matches: destinations(t) } : { kind: "unknown" });
}

function intentWords(t: string): Intent | null {
  if (has(t, ["dao han", "tien sap ve", "tien ve", "co tuc", "lai tien gui"])) return { kind: "money_in" };
  if (has(t, ["luan diem", "den xau", "chi bao xau", "xem lai"])) return { kind: "theses" };
  if (has(t, ["ban tin", "sau phien", "bao cao phien"])) return { kind: "report" };
  if (has(t, ["loi", "suc khoe he thong", "he thong", "nguon du lieu", "lich chay"])) return { kind: "health" };
  if (has(t, ["can de y", "hom nay co gi", "can lam", "viec can", "canh bao"])) return { kind: "today" };
  if (has(t, ["lai lo", "lai", "lo", "danh muc", "tai khoan", "hom nay"])) return { kind: "portfolio" };
  return null;
}

/** Pages whose words appear in the question, best first (the longest word matched first). */
export function destinations(t: string): Destination[] {
  const scored = DESTINATIONS.map((d) => ({ d, score: Math.max(0, ...d.keys.filter((k) => has(t, [k])).map((k) => k.length)) }))
    .filter((x) => x.score > 0).sort((a, b) => b.score - a.score);
  return scored.slice(0, 4).map((x) => x.d);
}
