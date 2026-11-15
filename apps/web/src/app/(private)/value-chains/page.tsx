import { ValueChains } from "../../../components/value-chains";

export default function ValueChainsPage() {
  return (
    <>
      <div className="pagehead"><h1>Chuỗi giá trị</h1><p className="muted">Đầu vào, trung gian, đầu ra của từng ngành theo tài liệu công khai, và vĩ mô đang tốt hay xấu cho ngành.</p></div>
      <ValueChains />
    </>
  );
}
