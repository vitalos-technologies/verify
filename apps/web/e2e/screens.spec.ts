// Captures the applicant journey for review (not an assertion suite). Run: SCREENS_DIR=... npx playwright test screens
import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const API = "http://localhost:8100";
const OUT = process.env.SCREENS_DIR;
test.skip(!OUT, "set SCREENS_DIR to capture screenshots");
test.use({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });

test("capture applicant journey", async ({ page }) => {
  const seed = JSON.parse(readFileSync(join(__dirname, ".state/seed.json"), "utf8"));
  const r = await fetch(`${API}/v1/verifications`, {
    method: "POST",
    headers: { Authorization: `Bearer ${seed.api_key}`, "Idempotency-Key": `shot-${Date.now()}`, "Content-Type": "application/json" },
    body: JSON.stringify({ external_reference: "shot", policy_id: "workforce_identity", policy_version: 1, country: "ZZ", document_type: "passport" }),
  });
  const body = await r.json();
  const shot = (n: string) => page.screenshot({ path: join(OUT!, `${n}.png`), fullPage: true });
  await page.goto(new URL(body.hosted_url).pathname);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/confirm your identity/i);
  await shot("01-intro");
  await page.getByRole("button", { name: "Start" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await shot("02-notice-error");
  await page.getByLabel("I've read this").check();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`shot.${Date.now()}@synthetic.example`);
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByLabel(/6-digit code/)).toBeVisible();
  await shot("03-email-code");
  const { code } = await (await fetch(`${API}/dev/last-contact-code`)).json();
  await page.getByLabel(/6-digit code/).fill(code);
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/document and selfie/i);
  await page.getByRole("button", { name: "Use my phone" }).click();
  await expect(page.getByRole("img", { name: /QR code/ })).toBeVisible();
  await shot("04-capture-handoff-qr");
  await page.getByRole("button", { name: "Use camera" }).click();
  await expect(page.getByRole("group", { name: /test capture/i })).toBeVisible();
  await shot("05-capture-synthetic");
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^checking$/i);
  await shot("06-processing");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^done$/i, { timeout: 15000 });
  await shot("07-complete");
});
