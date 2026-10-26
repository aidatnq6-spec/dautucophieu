"use client";

export type ApiFailure = { status: number; code: string; message: string; fields: string[] };
export class ApiError extends Error {
  constructor(public readonly failure: ApiFailure) { super(failure.message); }
}

let csrf: Promise<string> | null = null;
async function csrfToken(): Promise<string> {
  csrf ??= fetch("/api/session", { cache: "no-store", credentials: "same-origin" })
    .then(async (r) => { if (!r.ok) throw new Error(); return (await r.json()).csrfToken as string; })
    .catch((e) => { csrf = null; throw e; });
  return csrf;
}

function clearCsrf() {
  csrf = null;
}

async function request(path: string, method: "GET" | "POST" | "PUT", body: unknown, retryCsrf: boolean): Promise<Response> {
  const headers: Record<string, string> = {};
  if (method !== "GET") {
    headers["content-type"] = "application/json";
    headers["x-csrf-token"] = await csrfToken();
  }
  const response = await fetch(`/api/internal/${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store", credentials: "same-origin" });
  if (retryCsrf && method !== "GET" && response.status === 403) {
    const failure = await response.clone().json().catch(() => ({}));
    if (failure.code === "invalid_csrf") {
      clearCsrf();
      return request(path, method, body, false);
    }
  }
  return response;
}

/** Calls the Python business API through the authenticated Next proxy. */
export async function api<T>(path: string, init: { method?: "GET" | "POST" | "PUT"; body?: unknown } = {}): Promise<T> {
  const method = init.method ?? "GET";
  let response: Response;
  try {
    response = await request(path, method, init.body, true);
  } catch {
    throw new ApiError({ status: 0, code: "network", message: "Không kết nối được ứng dụng.", fields: [] });
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError({ status: response.status, code: data.code ?? "error", message: data.message ?? "Có lỗi xảy ra.", fields: data.fields ?? [] });
  }
  return data as T;
}

export function requestId(): string {
  return crypto.randomUUID().replaceAll("-", "");
}
