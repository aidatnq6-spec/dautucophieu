import { firebaseAuth } from "../../../lib/server/firebase-admin";
import { sessionConfig } from "../../../lib/server/session";
import { sessionHandlers } from "../../../lib/server/session-handlers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const POST = sessionHandlers(firebaseAuth, sessionConfig).logout;
