// Console: list, review queue, claim and decide; accessibility scans. Synthetic stack only.
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, request as pwRequest, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const API = "http://localhost:8100";
const seed = () => JSON.parse(readFileSync(join(__dirname, ".state/seed.json"), "utf8"));

async function axe(page: Page, label: string) {
  const res = await new AxeBuilder({ page: page as never }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  expect(res.violations.map((v) => `${label}: ${v.id} (${v.impact})`)).toEqual([]);
}

async function reviewCase(ref: string): Promise<string> {
  const s = seed();
  const r = await fetch(`${API}/v1/verifications`, {
    method: "POST",
    headers: { Authorization: `Bearer ${s.api_key}`, "Idempotency-Key": `con-${Date.now()}-${ref}`, "Content-Type": "application/json" },
    body: JSON.stringify({ external_reference: ref, policy_id: "workforce_identity", policy_version: 1, country: "ZZ", document_type: "passport" }),
  });
  const body = await r.json();
  const token = new URL(body.hosted_url).pathname.split("/").pop();
  const app = await pwRequest.newContext({ baseURL: API });
  await app.post("/applicant/exchange", { data: { token } });
  await app.post("/applicant/notice", { data: { notice_version: "notice-synthetic-1" } });
  await app.post("/applicant/contact/send", { data: { channel: "email", destination: `${ref}.${Date.now()}@synthetic.example` } });
  const { code } = await (await fetch(`${API}/dev/last-contact-code`)).json();
  await app.post("/applicant/contact/verify", { data: { code } });
  const att = await (await app.post("/applicant/attempts")).json();
  await app.post("/dummy-provider/capture", { data: { capture_token: att.capture_token, scenario: "liveness_inconclusive" } });
  await app.post(`/applicant/attempts/${att.attempt_id}/submitted`);
  await app.dispose();
  await expect.poll(async () => (await (await fetch(`${API}/v1/verifications/${body.session.id}`,
    { headers: { Authorization: `Bearer ${s.api_key}` } })).json()).state, { timeout: 15000 }).toBe("review_required");
  return body.session.id;
}

async function signIn(page: Page) {
  const s = seed();
  await page.goto("/app/login");
  await page.getByLabel("Organisation ID").fill(s.tenant_id);
  await page.getByLabel("User").fill(s.owner_subject);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Verifications" })).toBeVisible();
}

test("reviewer claims and decides a case; evidence stays unchanged", async ({ page }) => {
  const sid = await reviewCase(`case-${Date.now()}`);
  await signIn(page);
  await page.getByRole("tab", { name: "Needs review" }).click();
  await expect(page.getByRole("button").filter({ hasText: /^case-/ }).first()).toBeVisible({ timeout: 15000 });
  await page.getByRole("button").filter({ hasText: /^case-/ }).first().click();
  await expect(page.getByRole("complementary", { name: /^case-/ })).toBeVisible();
  await axe(page, "list");
  await page.getByRole("link", { name: /Review queue/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Review queue" })).toBeVisible();
  await axe(page, "reviews");
  await page.goto(`/app/cases/${sid}`);
  await expect(page.getByRole("button", { name: "Claim" })).toBeVisible();
  await page.getByRole("button", { name: "Claim" }).click();
  await expect(page.getByRole("button", { name: "Record decision" })).toBeVisible();
  await axe(page, "case-claimed");
  await page.getByLabel("Decline").check();
  await page.getByLabel("Reason", { exact: true }).fill("Liveness could not be confirmed");
  await page.getByRole("button", { name: "Record decision" }).click();
  await expect(page.locator(".titlerow .pill")).toHaveText("Not verified");
  await expect(page.locator(".list .row", { hasText: "Liveness" }).locator(".pill")).toHaveText("Review needed");
  const v = await (await fetch(`${API}/v1/verifications/${sid}`, { headers: { Authorization: `Bearer ${seed().api_key}` } })).json();
  expect(v.state).toBe("declined");
  expect(v.decision.method).toBe("evidence_review");
});

test("console screenshots", async ({ page }) => {
  const out = process.env.SCREENS_DIR;
  test.skip(!out, "set SCREENS_DIR");
  await page.setViewportSize({ width: 1280, height: 800 });
  const sid = await reviewCase(`shot-${Date.now()}`);
  await signIn(page);
  await page.screenshot({ path: join(out!, "10-console-list.png") });
  await page.getByRole("tab", { name: "Needs review" }).click();
  await page.getByRole("button").filter({ hasText: /^shot-/ }).first().click();
  await expect(page.getByRole("complementary", { name: /^shot-/ })).toBeVisible();
  await page.screenshot({ path: join(out!, "13-console-detail.png") });
  await page.getByRole("link", { name: /Review queue/ }).click();
  await expect(page.getByRole("button", { name: "Claim" }).first()).toBeVisible();
  await page.screenshot({ path: join(out!, "11-console-reviews.png") });
  await page.goto(`/app/cases/${sid}`);
  await page.getByRole("button", { name: "Claim" }).click();
  await expect(page.getByRole("button", { name: "Record decision" })).toBeVisible();
  await page.getByLabel("Reason for viewing").fill("Reviewing liveness result");
  await page.getByRole("button", { name: "View" }).first().click();
  await expect(page.getByRole("img", { name: "Document" })).toBeVisible();
  await page.screenshot({ path: join(out!, "12-console-case.png"), fullPage: true });
  // Platform consoles (seeded operator).
  await page.goto("/platform-login");
  await page.getByLabel("Operator").fill(seed().platform_admin_subject);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Operations" })).toBeVisible();
  await expect(page.getByText("Identity checks")).toBeVisible();
  await axe(page, "ops");
  await page.screenshot({ path: join(out!, "14-ops.png"), fullPage: true });
  await page.getByRole("link", { name: "Organisations" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Organisations" })).toBeVisible();
  await expect(page.getByRole("complementary")).toBeVisible();
  await axe(page, "admin");
  await page.screenshot({ path: join(out!, "15-admin.png"), fullPage: true });
  await page.goto("/");
  await axe(page, "home");
  await page.screenshot({ path: join(out!, "16-home.png") });
});
