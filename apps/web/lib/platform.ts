export async function plat<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/platform${path}`, {
    method: body === undefined ? "GET" : "POST", credentials: "same-origin", cache: "no-store",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401 && typeof window !== "undefined") window.location.assign("/platform-login");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message ?? "Request failed.");
  return data as T;
}
