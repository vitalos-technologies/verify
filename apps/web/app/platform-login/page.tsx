"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Brand } from "@/components/ui";
import { plat } from "@/lib/platform";

export default function PlatformLogin() {
  const router = useRouter();
  const [subject, setSubject] = useState("");
  const [error, setError] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try { await plat("/dev-login", { tenant_id: "-", user_subject: subject.trim() }); router.push("/ops"); }
    catch { setError("Sign-in failed."); }
  }
  return (
    <div className="hosted">
      <p style={{ textAlign: "center" }}><Brand /></p>
      <div className="card" style={{ paddingTop: 24 }}>
        <h1>Platform sign-in</h1>
        <p className="lead">Development only</p>
        {error && <p className="error-summary" role="alert">{error}</p>}
        <form onSubmit={submit}>
          <label htmlFor="op">Operator</label>
          <input id="op" type="text" value={subject} onChange={(e) => setSubject(e.target.value)} required />
          <button className="btn block" style={{ marginTop: 16 }} type="submit">Sign in</button>
        </form>
      </div>
    </div>
  );
}
