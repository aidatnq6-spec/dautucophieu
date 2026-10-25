import { NextRequest, NextResponse } from "next/server";
import { sessionAuth } from "../../../lib/server/firebase-admin";
import { sessionConfig } from "../../../lib/server/session";
import { bridgeConfig, proxyIdentity } from "../../../lib/server/python-client";
import { apiError } from "../../../lib/server/session-handlers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: NextRequest) {
  try {
    const data = await proxyIdentity(request, sessionAuth(), sessionConfig(), bridgeConfig());
    return NextResponse.json(data, { headers: { "Cache-Control": "no-store" } });
  } catch (error) { return apiError(error); }
}
