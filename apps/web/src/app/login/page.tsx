"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogIn } from "lucide-react";
import { getApps, initializeApp } from "firebase/app";
import { GoogleAuthProvider, getAuth, signInWithPopup, signOut } from "firebase/auth";

function firebaseApp() {
  const config = { apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY, authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID };
  if (!config.apiKey || !config.authDomain || !config.projectId) return null;
  return getApps()[0] ?? initializeApp(config);
}

export default function LoginPage() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function login() {
    const app = firebaseApp();
    if (!app) { setMessage("Chưa cấu hình Firebase phía trình duyệt (NEXT_PUBLIC_FIREBASE_*)."); return; }
    setBusy(true);
    setMessage(null);
    const auth = getAuth(app);
    try {
      const credential = await signInWithPopup(auth, new GoogleAuthProvider());
      const idToken = await credential.user.getIdToken(true);
      const { csrfToken } = await (await fetch("/api/session", { cache: "no-store" })).json();
      const response = await fetch("/api/session", { method: "POST", headers: { "content-type": "application/json", "x-csrf-token": csrfToken },
        body: JSON.stringify({ idToken }) });
      if (!response.ok) throw new Error((await response.json()).message ?? "Đăng nhập không thành công.");
      router.push("/onboarding");
    } catch (e) {
      setMessage(e instanceof Error && e.message ? e.message : "Đăng nhập không thành công.");
    } finally {
      // The browser keeps no Firebase session; the server session cookie is the only login state.
      await signOut(auth).catch(() => undefined);
      setBusy(false);
    }
  }

  return (
    <main className="content" style={{ maxWidth: 520 }}>
      <div className="surface">
        <h1>Đăng nhập</h1>
        <p className="muted">Ứng dụng cá nhân: chỉ tài khoản Google của chủ sở hữu đã cấu hình được vào.</p>
        {message && <p className="errors" role="alert">{message}</p>}
        <button className="btn primary" onClick={() => void login()} disabled={busy}><LogIn size={16} aria-hidden="true" />Đăng nhập bằng Google</button>
      </div>
    </main>
  );
}
