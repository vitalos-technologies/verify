"use client";

import { useRouter } from "next/navigation";
import QRCode from "qrcode";
import { useEffect, useRef, useState } from "react";

import { Brand } from "@/components/ui";
import { con, setCsrf } from "@/lib/console";

type Status = { enrolled: boolean; first_factor: string; account: string };

export default function Mfa() {
  const router = useRouter();
  const [status, setStatus] = useState<Status | null>(null);
  const [qr, setQr] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const s = await con<Status>("/mfa/status");
        setStatus(s);
        if (!s.enrolled) {
          const e = await con<{ secret: string; otpauth_uri: string }>("/mfa/enroll", {});
          setSecret(e.secret); setQr(await QRCode.toDataURL(e.otpauth_uri, { margin: 1, width: 200 }));
        }
      } catch { setError("Sign-in expired. Please start again."); }
      heading.current?.focus();
    })();
  }, []);

  async function verify(e: React.FormEvent) {
    e.preventDefault(); setError("");
    try {
      const r = await con<{ redirect: string }>("/mfa/verify", { code: code.trim() });
      const m = document.cookie.match(/(?:^|; )vv_csrf=([^;]+)/);
      if (m) setCsrf(decodeURIComponent(m[1]));
      router.push(r.redirect);
    } catch (err) { setError((err as Error).message); }
  }

  return (
    <div className="hosted">
      <p style={{ textAlign: "center" }}><Brand /></p>
      <div className="card" style={{ paddingTop: 24 }}>
        <h1 ref={heading} tabIndex={-1}>{status && !status.enrolled ? "Set up your authenticator" : "Enter your code"}</h1>
        {status && <p className="lead">{status.account}</p>}
        {status && !status.enrolled && qr && (<>
          <p>Scan with Google Authenticator, Microsoft Authenticator or 1Password.</p>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="qr" src={qr} alt="QR code for your authenticator app" />
          <p className="muted" style={{ textAlign: "center", wordBreak: "break-all" }}>Or enter key: <code>{secret}</code></p>
        </>)}
        {status ? (
          <form onSubmit={verify}>
            <label htmlFor="code">6-digit code</label>
            <input id="code" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
              onChange={(e) => setCode(e.target.value)} aria-invalid={!!error} required />
            {error && <p className="field-error" role="alert">{error}</p>}
            <button className="btn block" style={{ marginTop: 12 }} type="submit">Continue</button>
          </form>
        ) : error ? <p role="alert">{error} <a href="/app/login">Sign in</a></p> : <p className="muted">Loading</p>}
      </div>
    </div>
  );
}
