import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

// Synthetic fixture data only. Seeding is idempotent so this file runs with or without onboarding.spec.
test.describe.configure({ mode: "serial" });
const SCENARIO = { cash_flows: ["100000", "100000"], discount_rate: "0.10", terminal_growth: "0" };
const DRAFT = { entity_id: "FPT", model: "fcfe_dcf", valuation_date: "2026-10-23", required_margin: "0.2", tranche_fraction: "0.25", shares: 10,
  sources: ["doc-fpt-1"], scenarios: { down: { ...SCENARIO, discount_rate: "0.12" }, base: SCENARIO, up: { ...SCENARIO, discount_rate: "0.09" } } };
const CANDIDATE = { entity_id: "FPT", ticker: "FPT", exchange: "HOSE", industry: "tech",
  evidence: { source: "verified_audit", eligible: true, live_eligible: true, history_years: 10, gaps: [] }, metrics: null };

test.beforeEach(async ({ context }) => signIn(context));

test("seed synthetic owner data", async ({ page }) => {
  await seedOwner(page);
  if ((await call(page, "GET", "valuation/FPT")).status() === 404) {
    expect((await call(page, "PUT", "valuation/FPT/draft", { assumptions: DRAFT, expected_version: 0, request_id: "seed-v" })).ok()).toBe(true);
  }
  for (const id of ["rs1", "rs2"]) await call(page, "POST", "universe/proposals", { proposal_id: id, as_of: "2026-10-24", candidates: [CANDIDATE], request_id: `seed-${id}` });
});

test("overview puts the decision first, holdings below, and keeps holdings outside the universe", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Dữ liệu thị trường tổng hợp")).toBeVisible();
  const decision = page.getByRole("region", { name: /./ }).first();
  await expect(decision).toBeVisible();
  await expect(page.getByTestId("overview-FPT")).toContainText("Ngoài danh sách nghiên cứu");
  await expect(page.getByTestId("overview-FPT")).toContainText(/Lãi [\d.]+ đ/);  // gain labelled in words, not colour only
  await page.getByRole("button", { name: "Xem căn cứ FPT" }).click();
  await expect(page.getByTestId("reasons-FPT")).toContainText("Mã ngoài danh sách nghiên cứu");
  await expect(page.getByRole("button", { name: /^Mua/ })).toHaveCount(0);
});

test("approving valuation assumptions creates a version and sources trace to evidence", async ({ page }) => {
  await page.goto("/research/FPT");
  await expect(page.getByTestId("valuation")).toContainText("Bản nháp — chưa kích hoạt vùng giá");
  await page.getByRole("button", { name: "Duyệt giả định" }).click();
  await expect(page.getByTestId("valuation")).toContainText(/Đã duyệt · phiên bản \d+/);

  await page.goto("/");
  await page.getByRole("button", { name: "Xem căn cứ FPT" }).click();
  await page.getByTestId("reasons-FPT").getByRole("link", { name: "doc-fpt-1" }).click();
  await expect(page).toHaveURL(/\/research\/FPT#doc-fpt-1$/);
  await expect(page.locator("#doc-fpt-1")).toContainText("BCTC quý III/2026 (tổng hợp)");
});

test("universe approval creates a version; rejecting another proposal leaves it unchanged", async ({ page }) => {
  await page.goto("/research");
  await expect(page.getByTestId("active-universe")).toContainText("Chưa có danh sách được duyệt");
  await expect(page.getByTestId("proposal-rs1")).toContainText("evidence_not_verified");
  await page.getByRole("button", { name: "Duyệt đề xuất rs1" }).click();
  await expect(page.getByTestId("active-universe")).toContainText("Phiên bản 1");
  await expect(page.getByTestId("active-universe")).toContainText("Chưa đầy đủ");
  await page.getByRole("button", { name: "Từ chối đề xuất rs2" }).click();
  await expect(page.getByTestId("proposal-rs2")).toContainText("Đã từ chối");
  await expect(page.getByTestId("active-universe")).toContainText("Phiên bản 1");
});

test("an issuer without data shows limits, not a buy action", async ({ page }) => {
  await page.goto("/research/VNM");
  await expect(page.getByText("Chưa có giả định định giá")).toBeVisible();
  await expect(page.getByText("Chưa có tài liệu nguồn cho mã này")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Mua/ })).toHaveCount(0);
});
