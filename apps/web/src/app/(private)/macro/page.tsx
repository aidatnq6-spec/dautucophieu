import { MacroChain } from "../../../components/macro-chain";
import { MacroView } from "../../../components/macro-view";
import { MacroCalendar, RateSpread } from "../../../components/macro-extras";
import { MacroLiquidity } from "../../../components/macro-liquidity";
import { Sensitivity } from "../../../components/sensitivity";
import { RateCycle } from "../../../components/rate-cycle";
import { UsCalendar } from "../../../components/us-calendar";
import { hanoiDate } from "../../../lib/format";

export default function MacroPage() {
  return (
    <>
      <div className="pagehead"><h1>Chỉ báo vĩ mô đang tốt hay xấu?</h1><p className="muted">Leading indicator: giá trị hiện tại, xu hướng so với kỳ trước và đánh giá theo quy tắc của bạn.</p></div>
      <MacroChain />
      <Sensitivity />
      <RateCycle />
      <RateSpread />
      <MacroLiquidity />
      <UsCalendar today={hanoiDate()} />
      <MacroCalendar />
      <MacroView />
    </>
  );
}
