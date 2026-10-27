import { MacroChain } from "../../../components/macro-chain";
import { MacroView } from "../../../components/macro-view";
import { Sensitivity } from "../../../components/sensitivity";
import { RateCycle } from "../../../components/rate-cycle";

export default function MacroPage() {
  return (
    <>
      <div className="pagehead"><h1>Chỉ báo vĩ mô đang tốt hay xấu?</h1><p className="muted">Leading indicator: giá trị hiện tại, xu hướng so với kỳ trước và đánh giá theo quy tắc của bạn.</p></div>
      <MacroChain />
      <Sensitivity />
      <RateCycle />
      <MacroView />
    </>
  );
}
