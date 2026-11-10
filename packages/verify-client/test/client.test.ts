// AT-13: two Workforce tenants, out-of-order and duplicate events, tenant binding, identity-only mapping.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { type IdentityStatus, type Session, sign, type Store, toIdentityStatus, VerifyClient, verifyWebhook, WebhookProcessor, WebhookRejected } from "../src/index.ts";

const fx = JSON.parse(readFileSync(new URL("./fixtures/signature.json", import.meta.url), "utf8"));
const NOW = 1794300000;

class MemStore implements Store {
  events = new Set<string>();
  revs = new Map<string, number>();
  saved: IdentityStatus[] = [];
  async hasEvent(t: string, id: string) { return this.events.has(`${t}|${id}`); }
  async recordEvent(t: string, id: string) { this.events.add(`${t}|${id}`); }
  async latestRevision(t: string, v: string) { return this.revs.get(`${t}|${v}`) ?? 0; }
  async saveStatus(t: string, s: IdentityStatus) { this.revs.set(`${t}|${s.verificationId}`, s.revision); this.saved.push(s); }
}

function fakeApi(sessions: Record<string, Record<string, Session>>): (key: string) => typeof fetch {
  return (key) => (async (url: string | URL | Request) => {
    const id = String(url).split("/").pop()!;
    const s = sessions[key]?.[id];
    return new Response(JSON.stringify(s ?? { code: "not_found" }), { status: s ? 200 : 404 });
  }) as typeof fetch;
}

function event(tenant: string, id: string, resource: string, version: number, state: string) {
  const body = JSON.stringify({ id, type: "verification.completed", occurred_at: "2026-11-10T12:00:00Z", tenant_reference: tenant,
    resource_id: resource, resource_version: version, data: { state, reason_codes: [] } });
  return { body, headers: { "X-Vitalos-Timestamp": String(NOW), "X-Vitalos-Signature": sign(`secret-${tenant}`, NOW, body) } };
}

test("signature matches the Python implementation (cross-language fixture)", () => {
  assert.equal(sign(fx.secret, fx.timestamp, fx.body), fx.signature);
  const env = verifyWebhook(fx.body, { "x-vitalos-timestamp": String(fx.timestamp), "x-vitalos-signature": fx.signature },
    [fx.secret], "ten_fixture", fx.timestamp);
  assert.equal(env.resource_version, 3);
});

test("rejects bad signature, stale timestamp, tampered body and wrong tenant; accepts rotated secret", () => {
  const h = { "x-vitalos-timestamp": String(fx.timestamp), "x-vitalos-signature": fx.signature };
  assert.throws(() => verifyWebhook(fx.body, h, ["whsec_wrong"], "ten_fixture", fx.timestamp), WebhookRejected);
  assert.throws(() => verifyWebhook(fx.body, h, [fx.secret], "ten_fixture", fx.timestamp + 301), WebhookRejected);
  assert.throws(() => verifyWebhook(fx.body.replace("approved", "declined"), h, [fx.secret], "ten_fixture", fx.timestamp), WebhookRejected);
  assert.throws(() => verifyWebhook(fx.body, h, [fx.secret], "ten_other", fx.timestamp), WebhookRejected);
  assert.ok(verifyWebhook(fx.body, h, ["whsec_new", fx.secret], "ten_fixture", fx.timestamp));
});

test("two tenants with out-of-order and duplicate events keep the newest revision per tenant", async () => {
  const sessions = {
    "key-A": { ver_1: { id: "ver_1", external_reference: "worker-a", state: "approved", revision: 5, decision: { revision: 2, outcome: "approved", method: "alternative_method" } } as Session },
    "key-B": { ver_1: { id: "ver_1", external_reference: "worker-b", state: "declined", revision: 4, decision: { revision: 1, outcome: "declined", method: "automated" } } as Session },
  };
  const api = fakeApi(sessions);
  const storeA = new MemStore(), storeB = new MemStore();
  const a = new WebhookProcessor("ten_A", ["secret-ten_A"], new VerifyClient("https://verify.example", "key-A", api("key-A")), storeA);
  const b = new WebhookProcessor("ten_B", ["secret-ten_B"], new VerifyClient("https://verify.example", "key-B", api("key-B")), storeB);

  const newer = event("ten_A", "evt_2", "ver_1", 5, "approved");
  const older = event("ten_A", "evt_1", "ver_1", 3, "review_required");
  assert.equal((await a.handle(newer.body, newer.headers, NOW)).outcome, "applied");
  assert.equal((await a.handle(older.body, older.headers, NOW)).outcome, "stale");
  assert.equal((await a.handle(newer.body, newer.headers, NOW)).outcome, "duplicate");
  assert.equal(storeA.saved.length, 1);
  assert.equal(storeA.saved[0].identity, "verified_alternative_method");

  // Same resource ID under tenant B is independent; A's event cannot be replayed into B.
  await assert.rejects(b.handle(newer.body, newer.headers, NOW), WebhookRejected);
  const bEvt = event("ten_B", "evt_2", "ver_1", 4, "declined");
  const out = await b.handle(bEvt.body, bEvt.headers, NOW);
  assert.equal(out.outcome, "applied");
  assert.equal(out.status!.identity, "not_verified");
  assert.equal(storeA.saved.length, 1);
});

test("identity status never asserts work eligibility", () => {
  for (const state of ["approved", "declined", "review_required", "action_required", "expired", "processing"]) {
    const s = toIdentityStatus({ id: "v", external_reference: "r", state, revision: 1, decision: null });
    const text = JSON.stringify(s).toLowerCase();
    assert.ok(!/eligib|right[_ -]?to[_ -]?work":|work_permit|cleared/.test(text.replace("not a right-to-work", "")));
    assert.match(s.note, /Not a right-to-work/);
  }
});

test("a failed authoritative fetch does not swallow the retry (D-J)", async () => {
  let fail = true;
  const api = (async () => {
    if (fail) throw new Error("network");
    return new Response(JSON.stringify({ id: "ver_9", external_reference: "w", state: "approved", revision: 2, decision: null }), { status: 200 });
  }) as unknown as typeof fetch;
  const store = new MemStore();
  const p = new WebhookProcessor("ten_A", ["secret-ten_A"], new VerifyClient("https://verify.example", "k", api), store);
  const e = event("ten_A", "evt_retry", "ver_9", 2, "approved");
  await assert.rejects(p.handle(e.body, e.headers, NOW));
  fail = false;
  assert.equal((await p.handle(e.body, e.headers, NOW)).outcome, "applied");
  assert.equal((await p.handle(e.body, e.headers, NOW)).outcome, "duplicate");
});
