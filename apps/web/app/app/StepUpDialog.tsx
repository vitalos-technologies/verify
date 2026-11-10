"use client";

import { useEffect, useRef, useState } from "react";

import { con, onStepUp } from "@/lib/console";

/** Asks for a current authenticator code before sensitive actions, then lets the action retry. */
export default function StepUpDialog() {
  const ref = useRef<HTMLDialogElement>(null);
  const resolver = useRef<((ok: boolean) => void) | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    onStepUp(() => new Promise<boolean>((resolve) => {
      resolver.current = resolve; setCode(""); setError(""); ref.current?.showModal();
    }));
    return () => onStepUp(null);
  }, []);
  function close(ok: boolean) { ref.current?.close(); resolver.current?.(ok); resolver.current = null; }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try { await con("/mfa/step-up", { code: code.trim() }); close(true); } catch { setError("That code is not right."); }
  }
  return (
    <dialog ref={ref} className="panel" aria-labelledby="su-h" onCancel={() => close(false)} style={{ maxWidth: 380 }}>
      <form onSubmit={submit}>
        <h2 id="su-h">Confirm it&apos;s you</h2>
        <label htmlFor="su-code">Authenticator code</label>
        <input id="su-code" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
          onChange={(e) => setCode(e.target.value)} aria-invalid={!!error} autoFocus />
        {error && <p className="field-error" role="alert">{error}</p>}
        <div className="btnrow" style={{ marginTop: 16 }}>
          <button className="btn" type="submit">Confirm</button>
          <button className="btn secondary" type="button" onClick={() => close(false)}>Cancel</button>
        </div>
      </form>
    </dialog>
  );
}
