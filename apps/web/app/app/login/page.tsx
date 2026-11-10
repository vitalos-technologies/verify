"use client";

import { Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Brand } from "@/components/ui";
import { con, setCsrf } from "@/lib/console";

const DEV = process.env.NEXT_PUBLIC_DEV_LOGIN === "1";

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.9 6.1C12.5 13.6 17.8 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.7c4.3-4 6.9-9.9 6.9-17.1z" />
      <path fill="#FBBC05" d="M10.6 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.7c-2.1 1.4-4.8 2.3-8.5 2.3-6.2 0-11.5-4.1-13.4-9.9l-7.9 6.1C6.6 42.6 14.6 48 24 48z" />
    </svg>
  );
}

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [tenant, setTenant] = useState("");
  const [subject, setSubject] = useState("");

  async function magic(e: React.FormEvent) {
    e.preventDefault(); setError("");
    try { await con("/magic/start", { email: email.trim() }); setSent(true); }
    catch (err) { setError((err as Error).message); }
  }
  async function dev(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await con<{ csrf_token: string }>("/dev-login", { tenant_id: tenant.trim(), user_subject: subject.trim() });
      setCsrf(r.csrf_token); router.push("/app");
    } catch { setError("Sign-in failed."); }
  }

  return (
    <div className="hosted">
      <p style={{ textAlign: "center" }}><Brand /></p>
      <div className="card" style={{ paddingTop: 24 }}>
        <h1>Sign in</h1>
        <p className="lead">Customer workspace</p>
        <a className="btn secondary block" href="/console/oidc/start"><GoogleMark /> Continue with Google</a>
        <div className="muted" style={{ textAlign: "center", margin: "16px 0" }}>or</div>
        {sent ? (
          <p className="banner" role="status">Check your email for a sign-in link. Open it in this browser.</p>
        ) : (
          <form onSubmit={magic}>
            <label htmlFor="email">Work email</label>
            <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            {error && <p className="field-error" role="alert">{error}</p>}
            <button className="btn block" style={{ marginTop: 12 }} type="submit"><Mail size={18} aria-hidden /> Email me a link</button>
          </form>
        )}
        {DEV && (
          <form onSubmit={dev} style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
            <h2 style={{ marginTop: 12 }}>Development</h2>
            <label htmlFor="tenant">Organisation ID</label>
            <input id="tenant" type="text" value={tenant} onChange={(e) => setTenant(e.target.value)} required />
            <label htmlFor="subject">User</label>
            <input id="subject" type="text" value={subject} onChange={(e) => setSubject(e.target.value)} required />
            <button className="btn secondary block" style={{ marginTop: 16 }} type="submit">Sign in</button>
          </form>
        )}
      </div>
    </div>
  );
}
