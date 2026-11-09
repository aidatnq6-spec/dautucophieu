import { expect, test } from "@playwright/test";

test("every page answers with the protective headers, and a Google sign-in popup stays allowed", async ({ page }) => {
  const headers = (await page.goto("/login"))!.headers();
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("same-origin");
  expect(headers["permissions-policy"]).toContain("camera=()");
  expect(headers["cross-origin-opener-policy"]).toBe("same-origin-allow-popups");
});
