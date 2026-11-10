"use client";

// Applicant journey (04_user_experience §Applicant journey). Server state is authoritative:
// refreshing or switching device never loses progress, and nothing here decides an outcome.

import QRCode from "qrcode";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiFailure, type ApplicantView, call } from "@/lib/api";

type Mode = "hosted" | "handoff" | "resume";
type Problem = { field?: string; message: string };
type Fatal = "invalid" | "session_ended" | null;

const DOC_LABEL: Record<string, string> = { passport: "passport", driving_licence: "driving licence" };
const SCENARIOS: [string, string][] = [
  ["all_pass", "All pass"],
  ["low_quality", "Blurry photo"],
  ["liveness_inconclusive", "Liveness unclear"],
  ["face_no_match", "Face mismatch"],
  ["document_expired", "Expired document"],
  ["provider_outage", "Provider outage"],
];

export default function Journey({ mode, token }: { mode: Mode; token?: string }) {
  const [view, setView] = useState<ApplicantView | null>(null);
  const [fatal, setFatal] = useState<Fatal>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [busy, setBusy] = useState(false);
  const [introDone, setIntroDone] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [noticeRead, setNoticeRead] = useState(false);
  const [email, setEmail] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [code, setCode] = useState("");
  const [camera, setCamera] = useState<"unknown" | "checking" | "ok" | "unavailable">("unknown");
  const [scenario, setScenario] = useState("all_pass");
  const [handoff, setHandoff] = useState<{ url: string; qr: string } | null>(null);
  const [announce, setAnnounce] = useState("");
  const [online, setOnline] = useState(true);
  const heading = useRef<HTMLHeadingElement>(null);
  const started = useRef(false);

  const fail = useCallback((e: unknown, field?: string) => {
    if (e instanceof ApiFailure) {
      if (e.status === 401) return setFatal("session_ended");
      if (e.code === "link_invalid") return setFatal("invalid");
      setProblems([{ field, message: e.message }]);
      setAnnounce(e.message);
    } else {
      setProblems([{ message: "Something went wrong. Please try again." }]);
    }
  }, []);

  // Exchange the one-use token, then remove it from the address bar and history.
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        let v: ApplicantView;
        if (mode === "hosted") v = await call<ApplicantView>("/applicant/exchange", { method: "POST", body: { token } });
        else if (mode === "handoff") v = await call<ApplicantView>("/applicant/handoff/exchange", { method: "POST", body: { token } });
        else v = await call<ApplicantView>("/applicant/session");
        if (mode !== "resume") window.history.replaceState(null, "", "/v");
        setView(v);
      } catch (e) {
        if (e instanceof ApiFailure && e.status === 401 && mode === "resume") setFatal("session_ended");
        else if (e instanceof ApiFailure && (e.status === 404 || e.status === 401)) setFatal("invalid");
        else fail(e);
      }
    })();
  }, [mode, token, fail]);

  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    setOnline(navigator.onLine);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => { window.removeEventListener("online", up); window.removeEventListener("offline", down); };
  }, []);

  // Poll while the verification is being processed. Status changes are announced politely.
  useEffect(() => {
    if (view?.status !== "submitted") return;
    const id = window.setInterval(async () => {
      try {
        const v = await call<ApplicantView>("/applicant/session");
        if (v.status !== "submitted") setView(v);
      } catch (e) { if (e instanceof ApiFailure && e.status === 401) setFatal("session_ended"); }
    }, 3000);
    return () => window.clearInterval(id);
  }, [view?.status]);

  const step = deriveStep(view, fatal, introDone, retrying);
  useEffect(() => {
    setProblems([]);
    heading.current?.focus();
    if (step !== "loading") setAnnounce("");
  }, [step]);

  async function run(fn: () => Promise<void>, field?: string) {
    setBusy(true);
    setProblems([]);
    try { await fn(); } catch (e) { fail(e, field); } finally { setBusy(false); }
  }

  const acknowledge = () => run(async () => {
    if (!noticeRead) { setProblems([{ field: "notice-read", message: "Tick the box to continue." }]); return; }
    setView(await call<ApplicantView>("/applicant/notice", { method: "POST", body: { notice_version: view!.notice_version } }));
  }, "notice-read");

  const sendCode = () => run(async () => {
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) { setProblems([{ field: "email", message: "Enter a valid email." }]); return; }
    await call("/applicant/contact/send", { method: "POST", body: { channel: "email", destination: email } });
    setCodeSent(true);
    setAnnounce("Code sent.");
  }, "email");

  const verifyCode = () => run(async () => {
    if (!/^\d{6}$/.test(code.trim())) { setProblems([{ field: "code", message: "Enter the 6-digit code." }]); return; }
    await call("/applicant/contact/verify", { method: "POST", body: { code: code.trim() } });
    setView(await call<ApplicantView>("/applicant/session"));
    setAnnounce("Email confirmed.");
  }, "code");

  const checkCamera = () => run(async () => {
    setCamera("checking");
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("unsupported");
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      stream.getTracks().forEach((t) => t.stop()); // permission check only; nothing is recorded here
      setCamera("ok");
      setAnnounce("Camera available.");
    } catch {
      setCamera("unavailable");
      setAnnounce("We could not use a camera on this device.");
    }
  });

  const startHandoff = () => run(async () => {
    const r = await call<{ handoff_token: string }>("/applicant/handoff", { method: "POST" });
    const url = `${window.location.origin}/h/${r.handoff_token}`;
    setHandoff({ url, qr: await QRCode.toDataURL(url, { margin: 1, width: 200 }) });
    setAnnounce("QR code shown.");
  });

  const capture = () => run(async () => {
    const attempt = await call<{ attempt_id: string; provider: string; capture_token: string }>("/applicant/attempts", { method: "POST" });
    if (attempt.provider !== "dummy") throw new ApiFailure(503, "capture_unavailable", "Capture is not available yet. Please contact the requesting organisation.");
    await call("/dummy-provider/capture", { method: "POST", body: { capture_token: attempt.capture_token, scenario } });
    const v = await call<ApplicantView>(`/applicant/attempts/${attempt.attempt_id}/submitted`, { method: "POST" });
    setRetrying(false);
    setView(v);
    setAnnounce("Submitted.");
  });

  const org = view?.requesting_organisation ?? "The requesting organisation";
  const required = view?.required_steps ?? [];
  const progress = ["intro", "notice", "email", "capture", "processing"];
  const at = progress.indexOf(step);

  return (
    <main>
      <p className="brand">{view ? org : "Identity check"}</p>
      <p className="sr-only" aria-live="polite" role="status">{announce}</p>
      {!online && <p className="banner" role="status">Offline. Progress saved.</p>}
      {at >= 0 && (
        <ol className="steps" aria-label={`Step ${at + 1} of ${progress.length}`}>
          {progress.map((p, i) => <li key={p} data-done={i <= at} />)}
        </ol>
      )}
      {problems.length > 0 && (
        <div className="error-summary" role="alert" aria-labelledby="error-summary-title" tabIndex={-1}>
          <h2 id="error-summary-title">There is a problem</h2>
          <ul>{problems.map((p, i) => <li key={i}>{p.field ? <a href={`#${p.field}`}>{p.message}</a> : p.message}</li>)}</ul>
        </div>
      )}

      {step === "loading" && (<><h1 ref={heading} tabIndex={-1}>Loading</h1><div className="spinner" aria-hidden="true" /></>)}

      {step === "invalid" && (<>
        <h1 ref={heading} tabIndex={-1}>Link expired or already used</h1>
        <p>Ask the sender for a new link.</p>
      </>)}

      {step === "session_ended" && (<>
        <h1 ref={heading} tabIndex={-1}>Session ended</h1>
        <p>Progress saved. Open your link again.</p>
      </>)}

      {step === "intro" && view && (<>
        <h1 ref={heading} tabIndex={-1}>Confirm your identity</h1>
        <p className="muted">About 5 minutes · by {formatDate(view.expires_at)}</p>
        <ul>
          <li>Your {DOC_LABEL[view.document.type] ?? view.document.type}</li>
          <li>A selfie</li>
          {required.includes("email") && <li>Your email</li>}
        </ul>
        <button className="btn" onClick={() => setIntroDone(true)}>Start</button>
      </>)}

      {step === "notice" && view && (<>
        <h1 ref={heading} tabIndex={-1}>Your data</h1>
        <ul>
          <li>Checked by a verification provider for {org}</li>
          <li>Deleted after {org}&apos;s retention period</li>
          <li>Not a right-to-work check</li>
        </ul>
        <p className="muted">Draft notice ({view.notice_version})</p>
        <label className="check" htmlFor="notice-read">
          <input id="notice-read" type="checkbox" checked={noticeRead} onChange={(e) => setNoticeRead(e.target.checked)}
            aria-invalid={problems.some((p) => p.field === "notice-read")} />
          <span>I&apos;ve read this</span>
        </label>
        <button className="btn" onClick={acknowledge} disabled={busy}>Continue</button>
      </>)}

      {step === "email" && (<>
        <h1 ref={heading} tabIndex={-1}>Confirm your email</h1>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="email" inputMode="email" value={email}
          onChange={(e) => setEmail(e.target.value)} aria-invalid={problems.some((p) => p.field === "email")}
          aria-describedby={problems.some((p) => p.field === "email") ? "email-error" : undefined} />
        {problems.some((p) => p.field === "email") && <p id="email-error" className="field-error">{problems.find((p) => p.field === "email")!.message}</p>}
        <button className={codeSent ? "btn secondary" : "btn"} onClick={sendCode} disabled={busy}>{codeSent ? "Resend code" : "Send code"}</button>
        {codeSent && (<>
          <label htmlFor="code">6-digit code</label>
          <input id="code" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
            onChange={(e) => setCode(e.target.value)} aria-invalid={problems.some((p) => p.field === "code")} />
          <button className="btn" onClick={verifyCode} disabled={busy}>Confirm</button>
        </>)}
      </>)}

      {step === "capture" && view && (<>
        <h1 ref={heading} tabIndex={-1}>{retrying ? "Try again" : "Document and selfie"}</h1>
        {retrying && <p className="muted">Good light, no glare, whole document in view.</p>}

        {camera !== "ok" && (<>
          <button className="btn" onClick={checkCamera} disabled={busy || camera === "checking"}>Use camera</button>
          {camera === "unavailable" && (
            <div className="card" role="region" aria-labelledby="no-camera">
              <h2 id="no-camera">No camera available</h2>
              <p>Not an issue with your identity. Allow camera access or use your phone.</p>
            </div>
          )}
        </>)}

        {camera === "ok" && (
          <fieldset className="card dev">
            <legend>Test capture (development only)</legend>
            {SCENARIOS.map(([value, label]) => (
              <label key={value} className="check" htmlFor={`sc-${value}`}>
                <input type="radio" id={`sc-${value}`} name="scenario" value={value} checked={scenario === value} onChange={() => setScenario(value)} />
                <span>{label}</span>
              </label>
            ))}
            <button className="btn" onClick={capture} disabled={busy}>Submit</button>
          </fieldset>
        )}

        {!handoff ? (
          <button className="btn secondary" onClick={startHandoff} disabled={busy}>Use my phone</button>
        ) : (
          <div className="card">
            <p>Scan with your phone. Expires in 10 min.</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="qr" src={handoff.qr} alt="QR code to continue on your phone" />
            <p className="muted" style={{ wordBreak: "break-all" }}>{handoff.url}</p>
          </div>
        )}
      </>)}

      {step === "processing" && (<>
        <h1 ref={heading} tabIndex={-1}>Checking</h1>
        <div className="spinner" aria-hidden="true" />
        <p className="muted">You can close this page.</p>
      </>)}

      {step === "action_required" && (<>
        <h1 ref={heading} tabIndex={-1}>Please try again</h1>
        <p className="muted">The photos couldn&apos;t be checked.</p>
        <button className="btn" onClick={() => { setRetrying(true); setCamera("unknown"); }}>Try again</button>
      </>)}

      {step === "completed" && (<>
        <h1 ref={heading} tabIndex={-1}>Done</h1>
        <p>{org} will be in touch.</p>
      </>)}

      {step === "expired" && (<>
        <h1 ref={heading} tabIndex={-1}>Link expired</h1>
        <p>Ask {org} for a new one.</p>
      </>)}

      <footer>Can&apos;t do this online? Contact {view ? org : "the sender"}.</footer>
    </main>
  );
}

function deriveStep(view: ApplicantView | null, fatal: Fatal, introDone: boolean, retrying: boolean): string {
  if (fatal) return fatal;
  if (!view) return "loading";
  switch (view.status) {
    case "expired": case "cancelled": return "expired";
    case "completed": return "completed";
    case "submitted": return "processing";
    case "action_required": return retrying ? "capture" : "action_required";
  }
  if (view.status === "not_started" && !introDone && !view.notice_acknowledged) return "intro";
  if (!view.notice_acknowledged) return "notice";
  if (view.required_steps.includes("email") && !view.contact_verified.includes("email")) return "email";
  return "capture";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" });
}
