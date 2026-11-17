import { redirect } from "next/navigation";

/** The building page now lives in the Tòa nhà cho thuê tab of Vay & bất động sản; old links still arrive. */
export default function BuildingPage() {
  redirect("/loan?tab=toa-nha");
}
