// Vitalos Verify client for Workforce (VV-013, 26_API_contract_guide §Workforce integration).
// - Server-side only: the API key and webhook secrets live in Workforce server secrets.
// - Webhooks are verified (HMAC-SHA256, 5-minute tolerance), bound to the expected tenant,
//   de-duplicated by event ID and ordered by resource_version.
// - Before a consequential transition the latest result is fetched from the API (authoritative).
// - The mapped status describes identity assurance only. It is never right-to-work or eligibility.
import { createHmac, timingSafeEqual } from "node:crypto";

export type Envelope = {
  id: string; type: string; occurred_at: string; tenant_reference: string; resource_id: string;
  resource_version: number; data: { state: string; reason_codes: string[] };
};

export type Session = {
  id: string; external_reference: string; state: string; revision: number;
  decision: { revision: number; outcome: string; method: string } | null;
};

export type IdentityStatus = {
  verificationId: string;
  identity: "pending" | "verified" | "verified_alternative_method" | "not_verified" | "needs_review" | "retry_requested" | "expired";
  revision: number;
  note: "Identity check only. Not a right-to-work, qualification or background check.";
};

export class WebhookRejected extends Error {}

export function sign(secret: string, timestamp: number, rawBody: string): string {
  return "v1=" + createHmac("sha256", secret).update(`${timestamp}.${rawBody}`).digest("hex");
}

export function verifyWebhook(rawBody: string, headers: Record<string, string | undefined>, secrets: string[],
  expectedTenant: string, nowSeconds = Math.floor(Date.now() / 1000), toleranceSeconds = 300): Envelope {
  const h = Object.fromEntries(Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v]));
  const ts = Number(h["x-vitalos-timestamp"]);
  const given = (h["x-vitalos-signature"] ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  if (!Number.isInteger(ts) || Math.abs(nowSeconds - ts) > toleranceSeconds) throw new WebhookRejected("stale or missing timestamp");
  const ok = secrets.some((secret) => {
    const expected = Buffer.from(sign(secret, ts, rawBody));
    return given.some((g) => { const b = Buffer.from(g); return b.length === expected.length && timingSafeEqual(b, expected); });
  });
  if (!ok) throw new WebhookRejected("bad signature");
  const env = JSON.parse(rawBody) as Envelope;
  if (env.tenant_reference !== expectedTenant) throw new WebhookRejected("tenant mismatch");
  return env;
}

export function toIdentityStatus(s: Session): IdentityStatus {
  const base = { verificationId: s.id, revision: s.revision,
    note: "Identity check only. Not a right-to-work, qualification or background check." as const };
  switch (s.state) {
    case "approved":
      return { ...base, identity: s.decision?.method === "alternative_method" ? "verified_alternative_method" : "verified" };
    case "declined": return { ...base, identity: "not_verified" };
    case "review_required": return { ...base, identity: "needs_review" };
    case "action_required": return { ...base, identity: "retry_requested" };
    case "expired": case "cancelled": return { ...base, identity: "expired" };
    default: return { ...base, identity: "pending" };
  }
}

export interface Store {
  /** True if this event ID was already applied (read-only check). */
  hasEvent(tenant: string, eventId: string): Promise<boolean>;
  /** Records the event ID after its effect is saved (same transaction as saveStatus where possible). */
  recordEvent(tenant: string, eventId: string): Promise<void>;
  latestRevision(tenant: string, verificationId: string): Promise<number>;
  saveStatus(tenant: string, status: IdentityStatus): Promise<void>;
}

export class VerifyClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly fetchImpl: typeof fetch;

  constructor(baseUrl: string, apiKey: string, fetchImpl: typeof fetch = fetch) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.fetchImpl = fetchImpl;
  }

  private async req<T>(path: string, init?: RequestInit): Promise<T> {
    const r = await this.fetchImpl(`${this.baseUrl}${path}`, {
      ...init, headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!r.ok) throw new Error(`Verify API ${r.status}`);
    return (await r.json()) as T;
  }

  createVerification(workerReference: string, opts: { policyId: string; policyVersion: number; country: string; documentType: string },
    idempotencyKey: string): Promise<{ session: Session; hosted_url: string }> {
    return this.req("/v1/verifications", { method: "POST", headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ external_reference: workerReference, policy_id: opts.policyId, policy_version: opts.policyVersion,
        country: opts.country, document_type: opts.documentType }) });
  }

  getVerification(id: string): Promise<Session> {
    return this.req(`/v1/verifications/${encodeURIComponent(id)}`);
  }
}

/** One processor per Workforce tenant: its own Verify tenant reference, API key and webhook secrets. */
export class WebhookProcessor {
  private readonly tenantReference: string;
  private readonly secrets: string[];
  private readonly client: VerifyClient;
  private readonly store: Store;

  constructor(tenantReference: string, secrets: string[], client: VerifyClient, store: Store) {
    this.tenantReference = tenantReference;
    this.secrets = secrets;
    this.client = client;
    this.store = store;
  }

  async handle(rawBody: string, headers: Record<string, string | undefined>, now?: number):
    Promise<{ outcome: "applied" | "duplicate" | "stale" | "ignored"; status?: IdentityStatus }> {
    const env = verifyWebhook(rawBody, headers, this.secrets, this.tenantReference, now);
    if (await this.store.hasEvent(this.tenantReference, env.id)) return { outcome: "duplicate" };
    if (!env.type.startsWith("verification.")) {
      await this.store.recordEvent(this.tenantReference, env.id);
      return { outcome: "ignored" };
    }
    const known = await this.store.latestRevision(this.tenantReference, env.resource_id);
    if (env.resource_version <= known) {
      await this.store.recordEvent(this.tenantReference, env.id);
      return { outcome: "stale" };
    }
    // Authoritative read before any consequential workflow change; events can arrive out of order.
    // If this throws, nothing is recorded, so the sender's retry is processed (verifier finding D-J).
    const latest = await this.client.getVerification(env.resource_id);
    if (latest.revision <= known) {
      await this.store.recordEvent(this.tenantReference, env.id);
      return { outcome: "stale" };
    }
    const status = toIdentityStatus(latest);
    await this.store.saveStatus(this.tenantReference, status);
    await this.store.recordEvent(this.tenantReference, env.id);
    return { outcome: "applied", status };
  }
}
