"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Brand } from "@/components/ui";
import { con, setCsrf } from "@/lib/console";

// SSO (OIDC + MFA) is the sign-in route; the form is development-only.
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
    <div className="hosted">
      <p style={{ textAlign: "center" }}><Brand /></p>
      <div className="card" style={{ paddingTop: 24 }}>
        <h1>Sign in</h1>
        <p className="lead">Customer workspace</p>
        <a className="btn block" href="/console/oidc/start">Sign in with SSO</a>
        <form onSubmit={submit} style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
          <h2 style={{ marginTop: 12 }}>Development</h2>
          {error && <p className="error-summary" role="alert">{error}</p>}
          <label htmlFor="tenant">Organisation ID</label>
          <input id="tenant" type="text" value={tenant} onChange={(e) => setTenant(e.target.value)} required />
          <label htmlFor="subject">User</label>
          <input id="subject" type="text" value={subject} onChange={(e) => setSubject(e.target.value)} required />
          <button className="btn secondary block" style={{ marginTop: 16 }} type="submit">Sign in</button>
        </form>
      </div>
    </div>
  );
}
