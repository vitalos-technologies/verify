// Thin client for the applicant API (same-origin via Next.js rewrites; cookie is HttpOnly).

export type ApplicantView = {
  requesting_organisation: string;
  purpose: string;
  expires_at: string;
  status: "not_started" | "in_progress" | "submitted" | "action_required" | "completed" | "expired" | "cancelled";
  document: { country: string; type: string };
  required_steps: string[];
  notice_version: string;
  notice_acknowledged: boolean;
  contact_verified: string[];
  alternative_route: string;
};

export class ApiFailure extends Error {
  constructor(public status: number, public code: string, message: string, public retryAfter?: string | null) {
    super(message);
  }
}

export async function call<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method: init?.method ?? "GET",
      headers: init?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    throw new ApiFailure(0, "offline", "We couldn't reach the service. Check your connection; your progress is saved.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiFailure(res.status, data.code ?? "error", data.message ?? "Something went wrong. Please try again.",
      res.headers.get("Retry-After"));
  }
  return data as T;
}
