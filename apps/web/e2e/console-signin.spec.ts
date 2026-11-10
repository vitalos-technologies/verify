// Console sign-in chosen by the owner: email magic link (or Google), then an authenticator code.
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";
import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const API = "http://localhost:8100";
const seed = () => JSON.parse(readFileSync(join(__dirname, ".state/seed.json"), "utf8"));

function base32(s: string): Buffer {
  const A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const ch of s.replace(/=+$/, "")) bits += A.indexOf(ch).toString(2).padStart(5, "0");
  const out = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(out);
}
function totp(secret: string, offset = 0): string {
  const step = Math.floor(Date.now() / 30000) + offset;
  const msg = Buffer.alloc(8); msg.writeBigUInt64BE(BigInt(step));
  const h = createHmac("sha1", base32(secret)).update(msg).digest();
  const o = h[h.length - 1] & 15;
  return String(((h.readUInt32BE(o) & 0x7fffffff) % 1_000_000)).padStart(6, "0");
}
async function axe(page: Page, label: string) {
  const res = await new AxeBuilder({ page: page as never }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  expect(res.violations.map((v) => `${label}: ${v.id} (${v.impact})`)).toEqual([]);
}

test("magic link, authenticator enrolment and code sign-in", async ({ page }) => {
  const out = process.env.SCREENS_DIR;
  await page.goto("/app/login");
  await expect(page.getByRole("link", { name: "Continue with Google" })).toHaveAttribute("href", "/console/oidc/start");
  await axe(page, "login");
  if (out) await page.screenshot({ path: join(out, "20-login.png") });
  await page.getByLabel("Work email").fill(seed().owner_email);
  await page.getByRole("button", { name: "Email me a link" }).click();
  await expect(page.getByRole("status")).toContainText("Check your email");
  const { link } = await (await fetch(`${API}/dev/last-magic-link`)).json();
  await page.goto(new URL(link).pathname + new URL(link).search);
  await expect(page).toHaveURL(/\/app\/mfa$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Set up your authenticator");
  await expect(page.getByRole("img", { name: /QR code/ })).toBeVisible();
  await axe(page, "mfa-enrol");
  if (out) await page.screenshot({ path: join(out, "21-mfa-enrol.png") });
  const key = (await page.locator("code").textContent())!.trim();
  await page.getByLabel("6-digit code").fill("000000");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator(".field-error")).toContainText("not right");
  await page.getByLabel("6-digit code").fill(totp(key));
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Verifications" })).toBeVisible();
});
