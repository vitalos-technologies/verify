"use client";

import { Clock, Download, Layers, ShieldCheck, TriangleAlert, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import CaseSummary from "./CaseSummary";
import { Pill, Stat } from "@/components/ui";
import { con, type Session, when } from "@/lib/console";
import { STATE_LABEL, STATE_TONE } from "@/lib/labels";

const TABS: [string, string][] = [["", "All checks"], ["approved", "Verified"], ["review_required", "Needs review"], ["in_progress", "In progress"]];
type Stats = { total: number; verified: number; needs_review: number; in_progress: number };

function Verifications() {
  const q = (useSearchParams().get("q") ?? "").toLowerCase();
  const [tab, setTab] = useState("");
  const [items, setItems] = useState<Session[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    con<{ items: Session[]; next_cursor: string | null }>(`/verifications?limit=25${tab ? `&state=${tab}` : ""}`)
      .then((r) => { setItems(r.items); setCursor(r.next_cursor); }).catch(() => setItems([]));
    con<Stats>("/stats").then(setStats).catch(() => {});
  }, [tab]);
  useEffect(() => { setItems(null); load(); }, [load]);

  async function more() {
    const r = await con<{ items: Session[]; next_cursor: string | null }>(`/verifications?limit=25&cursor=${encodeURIComponent(cursor!)}${tab ? `&state=${tab}` : ""}`);
    setItems((x) => [...(x ?? []), ...r.items]); setCursor(r.next_cursor);
  }

  const shown = (items ?? []).filter((s) => !q || s.external_reference.toLowerCase().includes(q) || s.id.toLowerCase().includes(q));
  const period = new Date().toISOString().slice(0, 7);
  const passed = (s: Session) => s.checks.filter((c) => c.result === "pass").length;

  return (
    <main className={`page${selected ? " split" : ""}`}>
      <div className="col">
        <div className="pagehead">
          <div><h1>Verifications</h1><p className="sub">Track identity checks and resolve cases.</p></div>
          <div className="actions">
            <a className="btn secondary" href={`/console/exports/verifications.csv?period=${period}`}><Download size={18} aria-hidden /> Export</a>
            <button className="btn" onClick={() => setCreating(true)}>New verification</button>
          </div>
        </div>
        {creating && <NewVerification onClose={() => { setCreating(false); load(); }} />}
        <div className="stats">
          <Stat icon={Layers} label="Total checks:" value={stats?.total ?? "–"} />
          <Stat icon={ShieldCheck} label="Verified:" value={stats?.verified ?? "–"} />
          <Stat icon={TriangleAlert} label="Needs review:" value={stats?.needs_review ?? "–"} tone="warn" />
          <Stat icon={Clock} label="In progress:" value={stats?.in_progress ?? "–"} />
        </div>
        <div>
          <div className="tabs" role="tablist" aria-label="Filter">
            {TABS.map(([v, l]) => <button key={v} role="tab" aria-selected={tab === v} onClick={() => setTab(v)}>{l}</button>)}
          </div>
          {items === null ? <p className="empty">Loading</p> : shown.length === 0 ? <p className="empty">No verifications</p> : (
            <div className="tablewrap">
              <table>
                <thead><tr><th scope="col">Reference</th><th scope="col">Case</th><th scope="col">Checks</th><th scope="col">Status</th><th scope="col">Created</th></tr></thead>
                <tbody>
                  {shown.map((s) => (
                    <tr key={s.id} className="clickable" aria-selected={selected === s.id} onClick={() => setSelected(s.id)}>
                      <td><button className="linkbtn ref" style={{ textDecoration: "none", fontWeight: 650 }} onClick={() => setSelected(s.id)}>{s.external_reference}</button></td>
                      <td className="muted">{s.id.slice(-8).toUpperCase()}</td>
                      <td className="num">{passed(s)} of {s.checks.length}</td>
                      <td><Pill tone={STATE_TONE[s.state]}>{STATE_LABEL[s.state] ?? s.state}</Pill></td>
                      <td className="num">{when(s.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {cursor && <p><button className="btn secondary" onClick={more}>Load more</button></p>}
        </div>
      </div>
      {selected && <CaseSummary id={selected} onChange={load} />}
    </main>
  );
}

function NewVerification({ onClose }: { onClose: () => void }) {
  const [ref, setRef] = useState("");
  const [doc, setDoc] = useState("passport");
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError("");
    try {
      const r = await fetch("/console/verifications", { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID(), "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ external_reference: ref.trim(), policy_id: "workforce_identity", policy_version: 1, country: "ZZ", document_type: doc }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.message ?? "Could not create.");
      setUrl(d.hosted_url);
    } catch (err) { setError((err as Error).message); }
  }
  return (
    <section className="panel" aria-labelledby="new-h">
      <div className="pagehead"><h2 id="new-h">New verification</h2><button className="linkbtn actions" aria-label="Close" onClick={onClose}><X size={20} aria-hidden /></button></div>
      {url ? (<><p>Send this link to the applicant. It works once.</p><input type="text" readOnly value={url} aria-label="Applicant link" onFocus={(e) => e.target.select()} /></>) : (
        <form onSubmit={submit}>
          <label htmlFor="ref">Your reference</label>
          <input id="ref" type="text" value={ref} onChange={(e) => setRef(e.target.value)} required maxLength={128} />
          <label htmlFor="doc">Document</label>
          <select id="doc" value={doc} onChange={(e) => setDoc(e.target.value)}><option value="passport">Passport</option><option value="driving_licence">Driving licence</option></select>
          <p className="muted">Synthetic coverage (ZZ) only until a supplier is contracted.</p>
          {error && <p className="error-summary" role="alert">{error}</p>}
          <button className="btn" type="submit">Create link</button>
        </form>
      )}
    </section>
  );
}

function csrfToken(): string {
  try { const v = sessionStorage.getItem("vv_csrf"); if (v) return v; } catch { /* blocked */ }
  const m = document.cookie.match(/(?:^|; )vv_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

export default function Page() { return <Suspense><Verifications /></Suspense>; }
