import "server-only";
import { cert, getApps, initializeApp } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { SessionError, type SessionAuth } from "./session";

export function firebaseAuth(): SessionAuth {
  // Emulator signatures are intentionally not trusted by the application.
  if (process.env.FIREBASE_AUTH_EMULATOR_HOST) throw new SessionError(503, "auth_unavailable", "Cấu hình xác thực không được hỗ trợ.");
  const projectId = process.env.FIREBASE_PROJECT_ID;
  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
  const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, "\n");
  if (!projectId || !clientEmail || !privateKey) throw new SessionError(503, "auth_unavailable", "Chưa cấu hình Firebase phía máy chủ.");
  try {
    const name = "investment-auth";
    const app = getApps().find((app) => app.name === name) ?? initializeApp({ credential: cert({ projectId, clientEmail, privateKey }), projectId }, name);
    return getAuth(app);
  } catch { throw new SessionError(503, "auth_unavailable", "Không thể khởi tạo xác thực."); }
}
