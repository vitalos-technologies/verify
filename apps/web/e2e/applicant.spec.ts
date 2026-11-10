// AT-04 accessible capture + M03-T02 applicant journey, against the synthetic stack (dummy provider).
import AxeBuilder from "@axe-core/playwright";
import { expect, type Locator, type Page, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const API = "http://localhost:8100";
const seed = () => JSON.parse(readFileSync(join(__dirname, ".state/seed.json"), "utf8"));
let counter = 0;

async function createSession(): Promise<{ id: string; path: string }> {
  const r = await fetch(`${API}/v1/verifications`, {
    method: "POST",
    headers: { Authorization: `Bearer ${seed().api_key}`, "Idempotency-Key": `e2e-${Date.now()}-${++counter}`,
      "Content-Type": "application/json" },
    body: JSON.stringify({ external_reference: `e2e-${counter}`, policy_id: "workforce_identity", policy_version: 1,
      country: "ZZ", document_type: "passport" }),
  });
  expect(r.status).toBe(201);
  const body = await r.json();
  return { id: body.session.id, path: new URL(body.hosted_url).pathname };
}

async function apiState(id: string): Promise<string> {
  const r = await fetch(`${API}/v1/verifications/${id}`, { headers: { Authorization: `Bearer ${seed().api_key}` } });
  return (await r.json()).state;
}

async function axe(page: Page, label: string) {
  const res = await new AxeBuilder({ page: page as never }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  expect(res.violations.map((v) => `${label}: ${v.id} (${v.impact})`)).toEqual([]);
}

async function noHorizontalScroll(page: Page) {
  const [scroll, client] = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
  expect(scroll).toBeLessThanOrEqual(client);
}

// Keyboard activation only: focus the control, then press a key (no pointer events).
async function press(el: Locator, key = "Enter") {
  await el.focus();
  await el.page().keyboard.press(key);
}

async function heading(page: Page, text: RegExp) {
  const h = page.getByRole("heading", { level: 1 });
  await expect(h).toHaveText(text);
  await expect(h).toBeFocused(); // focus moves to each new step for screen-reader users
}

async function throughEmail(page: Page) {
  await heading(page, /confirm your email/i);
  await page.getByLabel("Email", { exact: true }).fill(`e2e.${Date.now()}.${++counter}@synthetic.example`);
  await press(page.getByRole("button", { name: "Send code" }));
  await expect(page.getByRole("status").first()).toContainText("Code sent");
  const { code } = await (await fetch(`${API}/dev/last-contact-code`)).json();
  await page.getByLabel(/6-digit code/).fill(code);
  await press(page.getByRole("button", { name: "Confirm" }));
}

test("keyboard-only journey completes; token removed from URL; accessible at each step", async ({ page, browser }) => {
  const s = await createSession();
  await page.goto(s.path);
  await heading(page, /confirm your identity/i);
  await expect(page).toHaveURL(/\/v$/);
  await axe(page, "intro");
  await noHorizontalScroll(page);
  await press(page.getByRole("button", { name: "Start" }));

  await heading(page, /your data/i);
  await press(page.getByRole("button", { name: "Continue" }));
  await expect(page.getByRole("alert", { name: "There is a problem" })).toContainText("Tick the box");
  await axe(page, "notice-error");
  await press(page.getByLabel("I've read this"), "Space");
  await press(page.getByRole("button", { name: "Continue" }));

  await throughEmail(page);
  await heading(page, /check it.s you/i);
  await axe(page, "capture");
  await noHorizontalScroll(page);
  await press(page.getByRole("button", { name: "Use camera" }));
  await expect(page.getByRole("group", { name: /test capture/i })).toBeVisible();
  await press(page.getByRole("button", { name: "Submit" }));

  await heading(page, /^checking$/i);
  await axe(page, "processing");
  await heading(page, /^done$/i);
  await axe(page, "completed");
  expect(await apiState(s.id)).toBe("approved");

  // The one-use link cannot be reused from another browser.
  const other = await browser.newContext();
  const p2 = await other.newPage();
  await p2.goto(s.path);
  await expect(p2.getByRole("heading", { level: 1 })).toHaveText(/expired or already used/i);
  await other.close();
});

test("camera denied: alternative and handoff offered, no adverse outcome, same session continues on phone",
  async ({ page, browser }) => {
    const s = await createSession();
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "mediaDevices", {
        value: { getUserMedia: () => Promise.reject(new DOMException("denied", "NotAllowedError")) },
      });
    });
    await page.goto(s.path);
    await press(page.getByRole("button", { name: "Start" }));
    await press(page.getByLabel("I've read this"), "Space");
    await press(page.getByRole("button", { name: "Continue" }));
    await throughEmail(page);
    await press(page.getByRole("button", { name: "Use camera" }));
    await expect(page.getByRole("region", { name: /no camera available/i })).toContainText("Not an issue with your identity");
    await axe(page, "camera-denied");
    expect(await apiState(s.id)).toBe("created"); // no fraud/decline from a device limitation

    await press(page.getByRole("button", { name: "Use my phone" }));
    const img = page.getByRole("img", { name: /QR code/ });
    await expect(img).toBeVisible();
    const link = (await page.locator("text=/\\/h\\/h_/").textContent())!.match(/https?:\/\/\S+/)![0];
    const phoneCtx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
    const phone = await phoneCtx.newPage();
    await phone.goto(link);
    await heading(phone, /check it.s you/i); // notice + email already done on the first device
    await press(phone.getByRole("button", { name: "Use camera" }));
    await press(phone.getByRole("button", { name: "Submit" }));
    await heading(phone, /^done$/i);
    await phoneCtx.close();
  });

test("retry after poor capture, then success", async ({ page }) => {
  const s = await createSession();
  await page.goto(s.path);
  await press(page.getByRole("button", { name: "Start" }));
  await press(page.getByLabel("I've read this"), "Space");
  await press(page.getByRole("button", { name: "Continue" }));
  await throughEmail(page);
  await press(page.getByRole("button", { name: "Use camera" }));
  await press(page.getByLabel("Blurry photo"), "Space");
  await press(page.getByRole("button", { name: "Submit" }));
  await heading(page, /please try again/i);
  await axe(page, "action-required");
  await press(page.getByRole("button", { name: "Try again" }));
  await heading(page, /^try again$/i);
  await press(page.getByRole("button", { name: "Use camera" }));
  await press(page.getByLabel("All pass"), "Space");
  await press(page.getByRole("button", { name: "Submit" }));
  await heading(page, /^done$/i);
  expect(await apiState(s.id)).toBe("approved");
});

test("invalid link and refresh keep server state", async ({ page }) => {
  await page.goto("/v/not-a-real-token");
  await heading(page, /expired or already used/i);
  await axe(page, "invalid");
  const s = await createSession();
  await page.goto(s.path);
  await press(page.getByRole("button", { name: "Start" }));
  await press(page.getByLabel("I've read this"), "Space");
  await press(page.getByRole("button", { name: "Continue" }));
  await heading(page, /confirm your email/i);
  await page.reload(); // refreshing does not lose progress (server state)
  await heading(page, /confirm your email/i);
});
