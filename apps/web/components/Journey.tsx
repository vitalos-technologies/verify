"use client";

// Applicant journey (04_user_experience §Applicant journey). Server state is authoritative:
// refreshing or switching device never loses progress, and nothing here decides an outcome.

import { Camera, Check, CircleHelp, Clock, FileText, IdCard, Mail, ScanFace, ShieldCheck, Sun, User } from "lucide-react";
import QRCode from "qrcode";
import { useCallback, useEffect, useRef, useState } from "react";

import { Brand } from "@/components/ui";
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
  const [showAlt, setShowAlt] = useState(false);
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

  const STEPS = ["Your details", "Identity check", "Complete"];
  const stepIndex = ["intro", "notice", "email"].includes(step) ? 0 : ["capture", "action_required", "processing"].includes(step) ? 1 : step === "completed" ? 2 : -1;
  const [altOpen, setAltOpen] = [showAlt, setShowAlt];

  return (
    <>
      <header className="hosted-top">
        <Brand href="#" />
        <span className="divider" aria-hidden="true" style={{ width: 1, height: 24, background: "var(--border)" }} />
        {view && <span className="who">Verification for <strong>{org}</strong></span>}
        <a className="help" href="#help"><CircleHelp size={20} aria-hidden /> Help</a>
      </header>
      <main className="hosted">
        <p className="sr-only" aria-live="polite" role="status">{announce}</p>
        {!online && <p className="offline" role="status">Offline. Progress saved.</p>}
        <div className="card">
          {stepIndex >= 0 && (
            <ol className="stepper" aria-label="Progress">
              {STEPS.map((label, i) => (
                <li key={label} aria-current={i === stepIndex ? "step" : undefined}>
                  {i < stepIndex && <span className="tick" aria-hidden="true"><Check size={14} /></span>}
                  {i + 1}. {label}{i < stepIndex && <span className="sr-only"> (done)</span>}
                </li>
              ))}
            </ol>
          )}
          {problems.length > 0 && (
            <div className="error-summary" role="alert" aria-labelledby="error-summary-title" tabIndex={-1} style={{ marginBottom: 16 }}>
              <h2 id="error-summary-title">There is a problem</h2>
              <ul>{problems.map((p, i) => <li key={i}>{p.field ? <a href={`#${p.field}`}>{p.message}</a> : p.message}</li>)}</ul>
            </div>
          )}

          {step === "loading" && (<><h1 ref={heading} tabIndex={-1} style={{ marginTop: 24 }}>Loading</h1><div className="spinner" aria-hidden="true" /></>)}

          {step === "invalid" && (<div style={{ paddingTop: 24 }}>
            <h1 ref={heading} tabIndex={-1}>Link expired or already used</h1>
            <p className="lead">Ask the sender for a new link.</p>
          </div>)}

          {step === "session_ended" && (<div style={{ paddingTop: 24 }}>
            <h1 ref={heading} tabIndex={-1}>Session ended</h1>
            <p className="lead">Progress saved. Open your link again.</p>
          </div>)}

          {step === "intro" && view && (<>
            <h1 ref={heading} tabIndex={-1}>Confirm your identity</h1>
            <p className="lead">About 5 minutes · by {formatDate(view.expires_at)}</p>
            <ul className="items">
              <li><IdCard size={22} aria-hidden /> Your {DOC_LABEL[view.document.type] ?? view.document.type}</li>
              <li><ScanFace size={22} aria-hidden /> A selfie</li>
              {required.includes("email") && <li><Mail size={22} aria-hidden /> Your email</li>}
            </ul>
            <div className="actions"><button className="btn" onClick={() => setIntroDone(true)}>Start</button></div>
          </>)}

          {step === "notice" && view && (<>
            <h1 ref={heading} tabIndex={-1}>Your data</h1>
            <p className="lead">Draft notice ({view.notice_version})</p>
            <ul className="items">
              <li><ShieldCheck size={22} aria-hidden /> Checked by a verification provider for {org}</li>
              <li><Clock size={22} aria-hidden /> Deleted after {org}&apos;s retention period</li>
              <li><FileText size={22} aria-hidden /> Not a right-to-work check</li>
            </ul>
            <label className="check" htmlFor="notice-read">
              <input id="notice-read" type="checkbox" checked={noticeRead} onChange={(e) => setNoticeRead(e.target.checked)}
                aria-invalid={problems.some((p) => p.field === "notice-read")} />
              <span>I&apos;ve read this</span>
            </label>
            <div className="actions"><button className="btn" onClick={acknowledge} disabled={busy}>Continue</button></div>
          </>)}

          {step === "email" && (<>
            <h1 ref={heading} tabIndex={-1}>Confirm your email</h1>
            <label htmlFor="email">Email</label>
            <input id="email" type="email" autoComplete="email" inputMode="email" value={email}
              onChange={(e) => setEmail(e.target.value)} aria-invalid={problems.some((p) => p.field === "email")}
              aria-describedby={problems.some((p) => p.field === "email") ? "email-error" : undefined} />
            {problems.some((p) => p.field === "email") && <p id="email-error" className="field-error">{problems.find((p) => p.field === "email")!.message}</p>}
            {codeSent && (<>
              <label htmlFor="code">6-digit code</label>
              <input id="code" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
                onChange={(e) => setCode(e.target.value)} aria-invalid={problems.some((p) => p.field === "code")} />
            </>)}
            <div className="actions">
              {codeSent && <button className="btn" onClick={verifyCode} disabled={busy}>Confirm</button>}
              <button className={codeSent ? "btn secondary" : "btn"} onClick={sendCode} disabled={busy}>{codeSent ? "Resend code" : "Send code"}</button>
            </div>
          </>)}

          {step === "capture" && view && (<>
            <h1 ref={heading} tabIndex={-1}>{retrying ? "Try again" : "Let\u2019s check it\u2019s you"}</h1>
            <p className="lead">{retrying ? "Good light, no glare, whole document in view." : "Have your document ready."}</p>
            <div className="frame"><div className="oval"><Camera size={32} aria-hidden /></div></div>
            <div className="tips">
              <span><User size={20} aria-hidden /> Face the camera</span>
              <span><Sun size={20} aria-hidden /> Even lighting</span>
              <span><ShieldCheck size={20} aria-hidden /> Face visible</span>
            </div>
            {camera === "unavailable" && (
              <div className="note" role="region" aria-labelledby="no-camera" style={{ marginTop: 16 }}>
                <strong id="no-camera">No camera available</strong>
                Not an issue with your identity. Allow camera access or use your phone.
              </div>
            )}
            {camera === "ok" && (
              <fieldset className="note" style={{ marginTop: 16, borderStyle: "dashed" }}>
                <legend>Test capture (development only)</legend>
                {SCENARIOS.map(([value, label]) => (
                  <label key={value} className="check" htmlFor={`sc-${value}`}>
                    <input type="radio" id={`sc-${value}`} name="scenario" value={value} checked={scenario === value} onChange={() => setScenario(value)} />
                    <span>{label}</span>
                  </label>
                ))}
              </fieldset>
            )}
            {handoff && (
              <div className="note" style={{ marginTop: 16, textAlign: "center" }}>
                <strong>Scan with your phone. Expires in 10 min.</strong>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="qr" src={handoff.qr} alt="QR code to continue on your phone" />
                <span className="muted" style={{ wordBreak: "break-all" }}>{handoff.url}</span>
              </div>
            )}
            <div className="actions">
              {camera === "ok"
                ? <button className="btn" onClick={capture} disabled={busy}>Submit</button>
                : <button className="btn" onClick={checkCamera} disabled={busy || camera === "checking"}>Use camera</button>}
              {!handoff && <button className="btn secondary" onClick={startHandoff} disabled={busy}>Use my phone</button>}
            </div>
          </>)}

          {step === "processing" && (<>
            <h1 ref={heading} tabIndex={-1}>Checking</h1>
            <p className="lead">You can close this page.</p>
            <div className="spinner" aria-hidden="true" />
          </>)}

          {step === "action_required" && (<>
            <h1 ref={heading} tabIndex={-1}>Please try again</h1>
            <p className="lead">The photos couldn&apos;t be checked.</p>
            <div className="actions"><button className="btn" onClick={() => { setRetrying(true); setCamera("unknown"); }}>Try again</button></div>
          </>)}

          {step === "completed" && (<>
            <h1 ref={heading} tabIndex={-1}>Done</h1>
            <p className="lead">{org} will be in touch.</p>
          </>)}

          {step === "expired" && (<>
            <h1 ref={heading} tabIndex={-1}>Link expired</h1>
            <p className="lead">Ask {org} for a new one.</p>
          </>)}

          {step !== "loading" && (
            <div className="actions" style={{ marginTop: 12 }}>
              <button className="linkbtn" aria-expanded={altOpen} onClick={() => setAltOpen(!altOpen)}>I need another way to verify</button>
              {altOpen && <p className="muted" role="status">Contact {view ? org : "the sender"} for another way.</p>}
            </div>
          )}

          <div className="foot" id="help">
            {view ? <>Your verification is requested by {org}.</> : "Identity check"}
            <br /><a href="#data">Privacy information</a>|<a href="#help">Get help</a>
          </div>
        </div>
      </main>
    </>
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
