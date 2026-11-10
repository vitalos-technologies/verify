import { Camera, Check, IdCard, Layers, ShieldCheck, User } from "lucide-react";
import Link from "next/link";

import { Brand, Logo } from "@/components/ui";

const ROWS: [string, string, string, string][] = [
  ["APP-10482", "Customer onboarding", "Verified", "good"],
  ["APP-10481", "Contractor onboarding", "Needs review", "warn"],
  ["APP-10480", "Customer onboarding", "Verified", "good"],
  ["APP-10479", "Partner onboarding", "Not verified", "bad"],
];

export default function Home() {
  return (
    <>
      <header className="site-top">
        <Brand />
        <nav aria-label="Site">
          <a href="#product">Product</a><a href="#workforce">Solutions</a><a href="#developers">Developers</a><a href="#pricing">Pricing</a>
        </nav>
        <div className="right">
          <Link className="signin" href="/app/login">Sign in</Link>
          <a className="btn" href="https://vitalos.co.uk">Book a demo</a>
        </div>
      </header>
      <main>
        <section className="hero">
          <div>
            <h1>Verify people.<br />Move business forward.</h1>
            <p>Identity checks, clear decisions and simpler onboarding — all in one workspace.</p>
            <div className="cta">
              <a className="btn" href="https://vitalos.co.uk">Book a demo</a>
              <a className="btn secondary" href="#product">Explore the platform</a>
            </div>
          </div>
          <div className="preview" aria-hidden="true">
            <div className="app">
              <div className="mrail">
                <span style={{ fontWeight: 700, padding: "0 8px 8px" }}><Logo size={22} /> Vitalos Verify</span>
                <span className="on"><User size={14} /> Verifications</span>
                <span><Layers size={14} /> Reviews</span>
              </div>
              <div className="mmain">
                <strong style={{ fontSize: "1rem" }}>Verifications</strong>
                <table style={{ marginTop: 8 }}>
                  <thead><tr><th>Reference</th><th>Workflow</th><th>Status</th></tr></thead>
                  <tbody>{ROWS.map(([r, w, s, t]) => (
                    <tr key={r}><td><strong>{r}</strong></td><td>{w}</td><td><span className="pill" data-tone={t}>{s}</span></td></tr>))}</tbody>
                </table>
              </div>
            </div>
            <div className="phone">
              <strong>Verify your identity</strong>
              <div className="progress" style={{ margin: "8px 0 12px" }}><span style={{ width: "50%" }} /></div>
              <div className="items" style={{ display: "grid", gap: 6 }}>
                <div className="note" style={{ display: "flex", gap: 8, alignItems: "center", padding: 8 }}><IdCard size={18} /> Government ID <Check size={16} style={{ marginLeft: "auto", color: "var(--good)" }} /></div>
                <div className="note" style={{ display: "flex", gap: 8, alignItems: "center", padding: 8 }}><Camera size={18} /> Selfie</div>
              </div>
            </div>
          </div>
        </section>
        <h2 className="section-title" id="product">One platform. Every verification step.</h2>
        <section className="features">
          <div><User size={34} strokeWidth={1.5} aria-hidden /><span><h3>Verify identity.</h3><p>Check documents, selfies and liveness with specialist providers.</p></span></div>
          <div><ShieldCheck size={34} strokeWidth={1.5} aria-hidden /><span><h3>Resolve exceptions.</h3><p>Review flagged cases with clear checks, evidence and accountable decisions.</p></span></div>
          <div id="developers"><Layers size={34} strokeWidth={1.5} aria-hidden /><span><h3>Connect your workflow.</h3><p>Signed webhooks and an idempotent API built for onboarding systems.</p></span></div>
        </section>
        <section className="features" id="workforce" style={{ paddingTop: 0 }}>
          <div id="pricing"><span><h3>Now in pilot.</h3><p>UK recruitment and contractor onboarding first. Pricing is agreed per pilot.</p></span></div>
        </section>
      </main>
      <footer className="site-foot">© Vitalos Technologies · Identity verification for modern business. Not a right-to-work, DBS or AML service.</footer>
    </>
  );
}
