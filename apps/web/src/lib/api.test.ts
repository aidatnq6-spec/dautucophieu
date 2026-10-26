import { beforeEach, expect, it, vi } from "vitest";

beforeEach(() => {
  vi.resetModules();
  vi.unstubAllGlobals();
});

it("refreshes an expired csrf token once and retries the mutation", async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ csrfToken: "old" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ code: "invalid_csrf", message: "expired" }), { status: 403 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ csrfToken: "new" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }));
  vi.stubGlobal("fetch", fetcher);

  const { api } = await import("./api");
  await expect(api("profile", { method: "PUT", body: { value: 1 } })).resolves.toEqual({ ok: true });

  expect(fetcher).toHaveBeenCalledTimes(4);
  expect(fetcher.mock.calls[1][1].headers["x-csrf-token"]).toBe("old");
  expect(fetcher.mock.calls[3][1].headers["x-csrf-token"]).toBe("new");
});

it("does not retry unrelated forbidden responses", async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ csrfToken: "token" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ code: "forbidden", message: "no" }), { status: 403 }));
  vi.stubGlobal("fetch", fetcher);

  const { ApiError, api } = await import("./api");
  await expect(api("profile", { method: "PUT", body: {} })).rejects.toBeInstanceOf(ApiError);
  expect(fetcher).toHaveBeenCalledTimes(2);
});
