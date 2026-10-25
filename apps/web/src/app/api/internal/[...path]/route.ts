import { NextRequest } from "next/server";
import { sessionAuth } from "../../../../lib/server/firebase-admin";
import { sessionConfig } from "../../../../lib/server/session";
import { bridgeConfig } from "../../../../lib/server/python-client";
import { proxyInternal } from "../../../../lib/server/python-proxy";
import { apiError } from "../../../../lib/server/session-handlers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function handle(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  try {
    return await proxyInternal(request, (await params).path, sessionAuth(), sessionConfig(), bridgeConfig());
  } catch (error) { return apiError(error); }
}
export const GET = handle;
export const POST = handle;
export const PUT = handle;
