import type { ReactNode } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AppNav } from "../../components/app-nav";
import { sessionAuth } from "../../lib/server/firebase-admin";
import { SESSION_COOKIE, sessionConfig, verifyOwnerSession } from "../../lib/server/session";

export const dynamic = "force-dynamic";

export default async function PrivateLayout({ children }: { children: ReactNode }) {
  try {
    await verifyOwnerSession((await cookies()).get(SESSION_COOKIE)?.value, sessionAuth(), sessionConfig());
  } catch {
    redirect("/login");
  }
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">Đầu tư<span> Cổ phiếu</span></div>
        <AppNav />
      </aside>
      <main className="content" id="main">{children}</main>
    </div>
  );
}
