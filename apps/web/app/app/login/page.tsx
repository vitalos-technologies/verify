"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { con, setCsrf } from "@/lib/console";

// Development sign-in. Replaced by the organisation's identity provider (OIDC + MFA) before pilot.
export default function Login() {
  const router = useRouter();
  const [tenant, setTenant] = useState("");
  const [subject, setSubject] = useState("");
  const [error, setError] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await con<{ csrf_token: string }>("/dev-login", { tenant_id: tenant.trim(), user_subject: subject.trim() });
      setCsrf(r.csrf_token);
      router.push("/app");
    } catch { setError("Sign-in failed."); }
  }
  return (
    <main>
      <h1>Sign in</h1>
      <p className="muted">Development only</p>
      {error && <p className="error-summary" role="alert">{error}</p>}
      <form onSubmit={submit}>
        <label htmlFor="tenant">Organisation ID</label>
        <input id="tenant" type="text" value={tenant} onChange={(e) => setTenant(e.target.value)} required />
        <label htmlFor="subject">User</label>
        <input id="subject" type="text" value={subject} onChange={(e) => setSubject(e.target.value)} required />
        <button className="btn" type="submit">Sign in</button>
      </form>
    </main>
  );
}
