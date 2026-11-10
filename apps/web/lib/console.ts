// Console API client: HttpOnly session cookie (Path=/console) + CSRF header for commands.
import { ApiFailure } from "@/lib/api";

const KEY = "vv_csrf";

export function setCsrf(token: string) { try { sessionStorage.setItem(KEY, token); } catch { /* storage blocked */ } }
function csrf(): string {
  try { const v = sessionStorage.getItem(KEY); if (v) return v; } catch { /* storage blocked */ }
  const m = typeof document !== "undefined" ? document.cookie.match(/(?:^|; )vv_csrf=([^;]+)/) : null;
  return m ? decodeURIComponent(m[1]) : "";
}

type StepUp = () => Promise<boolean>;
let stepUpHandler: StepUp | null = null;
/** The workspace layout registers a dialog that asks for an authenticator code (step-up). */
export function onStepUp(fn: StepUp | null) { stepUpHandler = fn; }

export async function con<T>(path: string, body?: unknown, method?: string, retried = false): Promise<T> {
  const m = method ?? (body === undefined ? "GET" : "POST");
  const res = await fetch(`/console${path}`, {
    method: m,
    headers: { ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...(m !== "GET" ? { "X-CSRF-Token": csrf() } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && data.code === "step_up_required" && !retried && stepUpHandler) {
    if (await stepUpHandler()) return con<T>(path, body, method, true);
  }
  const publicPath = ["/dev-login", "/magic", "/mfa"].some((p) => path.startsWith(p));
  if (res.status === 401 && data.code !== "step_up_required" && typeof window !== "undefined" && !publicPath) window.location.assign("/app/login");
  if (!res.ok) throw new ApiFailure(res.status, data.code ?? "error", data.message ?? "Something went wrong.");
  return data as T;
}

export type Check = { id: string; type: string; result: string; reasons: string[]; provider_version?: string };
export type Decision = { revision: number; outcome: string; method: string; actor_type: string; reason_codes: string[]; decided_at: string } | null;
export type Session = { id: string; external_reference: string; state: string; revision: number; policy_id: string;
  policy_version: number; created_at: string; expires_at: string; checks: Check[]; decision: Decision };
export type Review = { id: string; session_id: string; status: string; assignee: string | null; lock_version: number; created_at: string };

export const LABEL: Record<string, string> = {
  government_id: "ID document", face_match: "Face match", liveness: "Liveness", email: "Email", phone: "Phone",
  review_required: "Needs review", action_required: "Retry requested", in_progress: "In progress",
  created: "Sent", processing: "Processing", approved: "Approved", declined: "Declined", expired: "Expired",
  cancelled: "Cancelled", error: "Provider error", evidence_review: "Evidence review",
  alternative_method: "Alternative method", automated: "Automated",
};

export const when = (iso: string) => new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" });
