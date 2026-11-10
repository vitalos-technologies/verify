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
const STEP_LABEL: Record<string, string> = {
  government_id: "Photo of your identity document",
  face_match: "A selfie to compare with the document photo",
  liveness: "A short live check that you are present",
  email: "A code sent to your email address",
  phone: "A code sent to your phone",
};
const SCENARIOS: [string, string][] = [
  ["all_pass", "All checks pass"],
  ["low_quality", "Blurry document photo (asks to retry)"],
  ["liveness_inconclusive", "Liveness inconclusive (goes to review)"],
  ["face_no_match", "Face does not match (goes to review)"],
  ["document_expired", "Expired document"],
  ["provider_outage", "Provider outage (delayed)"],
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
    if (!noticeRead) { setProblems([{ field: "notice-read", message: "Confirm that you have read the privacy notice." }]); return; }
    setView(await call<ApplicantView>("/applicant/notice", { method: "POST", body: { notice_version: view!.notice_version } }));
  }, "notice-read");

  const sendCode = () => run(async () => {
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) { setProblems([{ field: "email", message: "Enter an email address in the correct format, like name@example.com." }]); return; }
    await call("/applicant/contact/send", { method: "POST", body: { channel: "email", destination: email } });
    setCodeSent(true);
    setAnnounce("If the address is valid, a 6-digit code has been sent. It expires in 10 minutes.");
  }, "email");

  const verifyCode = () => run(async () => {
    if (!/^\d{6}$/.test(code.trim())) { setProblems([{ field: "code", message: "Enter the 6-digit code from the email." }]); return; }
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
    setAnnounce("A code to continue on your phone is shown. It works once and expires in 10 minutes.");
  });

  const capture = () => run(async () => {
    const attempt = await call<{ attempt_id: string; provider: string; capture_token: string }>("/applicant/attempts", { method: "POST" });
    if (attempt.provider !== "dummy") throw new ApiFailure(503, "capture_unavailable", "Capture is not available yet. Please contact the requesting organisation.");
    await call("/dummy-provider/capture", { method: "POST", body: { capture_token: attempt.capture_token, scenario } });
    const v = await call<ApplicantView>(`/applicant/attempts/${attempt.attempt_id}/submitted`, { method: "POST" });
    setRetrying(false);
    setView(v);
    setAnnounce("Submitted. We are checking your details.");
  });

  const org = view?.requesting_organisation ?? "The requesting organisation";
  const required = view?.required_steps ?? [];
  const progress = ["intro", "notice", "email", "capture", "processing"];
  const at = progress.indexOf(step);

  return (
    <main>
      <p className="brand">Identity check{view ? ` for ${org}` : ""}</p>
      <p className="sr-only" aria-live="polite" role="status">{announce}</p>
      {!online && <p className="banner" role="status">You are offline. Your progress is saved — reconnect to continue.</p>}
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

      {step === "loading" && (<><h1 ref={heading} tabIndex={-1}>Loading your identity check</h1><div className="spinner" aria-hidden="true" /></>)}

      {step === "invalid" && (<>
        <h1 ref={heading} tabIndex={-1}>This link has expired or was already used</h1>
        <p>For your security, each link works once. Ask the organisation that sent it for a new link.</p>
      </>)}

      {step === "session_ended" && (<>
        <h1 ref={heading} tabIndex={-1}>Your session has ended</h1>
        <p>Your progress is saved. Open the link you were sent again, or ask the organisation for a new one.</p>
      </>)}

      {step === "intro" && view && (<>
        <h1 ref={heading} tabIndex={-1}>{org} has asked you to confirm your identity</h1>
        <p>Purpose: {view.purpose.toLowerCase()}. This takes about 5 minutes.</p>
        <div className="card">
          <h2>You will need</h2>
          <ul>
            <li>Your {DOC_LABEL[view.document.type] ?? view.document.type}</li>
            {required.map((s) => <li key={s}>{STEP_LABEL[s] ?? s}</li>)}
          </ul>
        </div>
        <p className="muted">Complete this by {formatDate(view.expires_at)}.</p>
        <p>{view.alternative_route}</p>
        <button className="btn" onClick={() => setIntroDone(true)}>Continue</button>
      </>)}

      {step === "notice" && view && (<>
        <h1 ref={heading} tabIndex={-1}>How your information is used</h1>
        <div className="card">
          <p><strong>Placeholder notice ({view.notice_version}).</strong> The final wording will be approved by {org} as controller before any real use.</p>
          <ul>
            <li>{org} asked for this check to confirm your identity for onboarding.</li>
            <li>Your document and selfie are checked by a specialist verification provider acting for {org}.</li>
            <li>Images are kept only as long as {org}&apos;s retention policy allows, then deleted.</li>
            <li>The result is one input to {org}&apos;s decision. It is not a right-to-work or background check.</li>
            <li>You can ask {org} for another way to prove your identity, or to challenge a result.</li>
          </ul>
        </div>
        <label className="check" htmlFor="notice-read">
          <input id="notice-read" type="checkbox" checked={noticeRead} onChange={(e) => setNoticeRead(e.target.checked)}
            aria-invalid={problems.some((p) => p.field === "notice-read")} />
          <span>I have read how my information will be used</span>
        </label>
        <button className="btn" onClick={acknowledge} disabled={busy}>Continue</button>
        <p className="muted">Prefer not to continue online? {view.alternative_route}</p>
      </>)}

      {step === "email" && (<>
        <h1 ref={heading} tabIndex={-1}>Confirm your email address</h1>
        <p>This confirms you can receive email at this address. It does not prove who you are.</p>
        <label htmlFor="email">Email address</label>
        <input id="email" type="email" autoComplete="email" inputMode="email" value={email}
          onChange={(e) => setEmail(e.target.value)} aria-invalid={problems.some((p) => p.field === "email")}
          aria-describedby={problems.some((p) => p.field === "email") ? "email-error" : undefined} />
        {problems.some((p) => p.field === "email") && <p id="email-error" className="field-error">{problems.find((p) => p.field === "email")!.message}</p>}
        <button className={codeSent ? "btn secondary" : "btn"} onClick={sendCode} disabled={busy}>{codeSent ? "Send a new code" : "Send code"}</button>
        {codeSent && (<>
          <label htmlFor="code">6-digit code <span className="hint">Check your inbox and spam folder</span></label>
          <input id="code" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
            onChange={(e) => setCode(e.target.value)} aria-invalid={problems.some((p) => p.field === "code")} />
          <button className="btn" onClick={verifyCode} disabled={busy}>Confirm code</button>
        </>)}
      </>)}

      {step === "capture" && view && (<>
        <h1 ref={heading} tabIndex={-1}>{retrying ? "Let's try that again" : "Check your document and face"}</h1>
        {retrying && <p>We couldn&apos;t complete the last attempt. Use good light, avoid glare and keep the whole document in view.</p>}
        <p>You&apos;ll photograph your {DOC_LABEL[view.document.type] ?? view.document.type}, then take a short selfie.</p>

        {camera !== "ok" && (<>
          <button className="btn" onClick={checkCamera} disabled={busy || camera === "checking"}>Use this device&apos;s camera</button>
          {camera === "unavailable" && (
            <div className="card" role="region" aria-labelledby="no-camera">
              <h2 id="no-camera">We couldn&apos;t use a camera on this device</h2>
              <p>This is not a problem with your identity. You can allow camera access and try again, continue on your phone, or ask {org} for another way.</p>
            </div>
          )}
        </>)}

        {camera === "ok" && (
          <fieldset className="card dev">
            <legend>Synthetic test capture (development only)</legend>
            <p className="muted">No real supplier is connected. Choose a synthetic outcome; no images are taken.</p>
            {SCENARIOS.map(([value, label]) => (
              <label key={value} className="check" htmlFor={`sc-${value}`}>
                <input type="radio" id={`sc-${value}`} name="scenario" value={value} checked={scenario === value} onChange={() => setScenario(value)} />
                <span>{label}</span>
              </label>
            ))}
            <button className="btn" onClick={capture} disabled={busy}>Submit</button>
          </fieldset>
        )}

        <h2>Other options</h2>
        {!handoff ? (
          <button className="btn secondary" onClick={startHandoff} disabled={busy}>Continue on my phone instead</button>
        ) : (
          <div className="card">
            <p>Scan this code with your phone camera. It works once and expires in 10 minutes. You won&apos;t lose progress here.</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="qr" src={handoff.qr} alt="QR code to continue this identity check on your phone" />
            <p className="muted">Or open this link on your phone: <span style={{ wordBreak: "break-all" }}>{handoff.url}</span></p>
          </div>
        )}
        <p>{view.alternative_route}</p>
      </>)}

      {step === "processing" && (<>
        <h1 ref={heading} tabIndex={-1}>Checking your details</h1>
        <div className="spinner" aria-hidden="true" />
        <p>This usually takes under a minute, but can take longer. You can close this page — {org} will be told when it is finished.</p>
      </>)}

      {step === "action_required" && (<>
        <h1 ref={heading} tabIndex={-1}>We need you to try again</h1>
        <p>We couldn&apos;t complete the check with what was submitted. This can happen because of lighting, glare or an unreadable photo.</p>
        <button className="btn" onClick={() => { setRetrying(true); setCamera("unknown"); }}>Try again</button>
        <p className="muted">If you can&apos;t complete this online: {view?.alternative_route}</p>
      </>)}

      {step === "completed" && (<>
        <h1 ref={heading} tabIndex={-1}>Thank you — your check is complete</h1>
        <p>{org} will let you know what happens next. If you have questions or want to challenge the result, contact {org}.</p>
      </>)}

      {step === "expired" && (<>
        <h1 ref={heading} tabIndex={-1}>This identity check is no longer available</h1>
        <p>It has expired or was cancelled. Ask {org} for a new link if you still need to complete it.</p>
      </>)}

      <footer>Need help? Contact {org}. Identity checks are provided by Vitalos Verify on their behalf.</footer>
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
