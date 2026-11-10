"use client";

import { Camera, FileText, FlaskConical, IdCard, Layers, Mail, Nfc, TriangleAlert, Users } from "lucide-react";
import { useEffect, useState } from "react";

import { ago, Pill, Stat } from "@/components/ui";
import { plat } from "@/lib/platform";

type Org = { id: string; name: string; status: string; plan: string; enabled_checks: number; total_checks: number;
  capabilities: { key: string; label: string; enabled: boolean }[]; monthly_usage: number; monthly_cap: number; members: number };
type Data = { items: Org[]; stats: { active: number; pilot: number; monthly_verifications: number; attention: number } };
const CAP_ICON: Record<string, typeof IdCard> = { government_id: IdCard, liveness: Camera, email: Mail, document: FileText, nfc: Nfc };
const STATUS: Record<string, string> = { active: "Active", attention: "Attention", suspended: "Suspended", billing_hold: "Billing hold" };
const ACTION: Record<string, string> = {
  "policy.publish": "Policy published", "api_key.create": "API key created", "api_key.revoke": "API key revoked",
  "membership.revoke": "Member removed", "webhook.create": "Webhook added", "billing.invoice": "Invoice issued",
  "billing.credit": "Credit issued", "legal_hold.place": "Legal hold placed", "console.sign_in": "Signed in (SSO)",
};

export default function Organisations() {
  const [d, setD] = useState<Data | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [activity, setActivity] = useState<{ action: string; at: string }[]>([]);
  useEffect(() => { plat<Data>("/organisations").then((x) => { setD(x); setSel(x.items[0]?.id ?? null); }).catch(() => {}); }, []);
  useEffect(() => { if (sel) plat<{ items: { action: string; at: string }[] }>(`/organisations/${sel}/activity`).then((r) => setActivity(r.items)).catch(() => setActivity([])); }, [sel]);
  const org = d?.items.find((o) => o.id === sel);
  return (
    <main className={`page${org ? " split" : ""}`}>
      <div className="col">
        <div className="pagehead"><div><h1>Organisations</h1><p className="sub">Manage customers and platform access.</p></div></div>
        <div className="stats">
          <Stat icon={Users} label="Active organisations:" value={d?.stats.active ?? "–"} />
          <Stat icon={FlaskConical} label="Pilot accounts:" value={d?.stats.pilot ?? "–"} />
          <Stat icon={Layers} label="Monthly verifications:" value={d?.stats.monthly_verifications.toLocaleString("en-GB") ?? "–"} />
          <Stat icon={TriangleAlert} label="Needing attention:" value={d?.stats.attention ?? "–"} tone="warn" />
        </div>
        <div className="panel flush"><div className="tablewrap"><table>
          <thead><tr><th scope="col">Organisation</th><th scope="col">Plan</th><th scope="col">Enabled checks</th><th scope="col">Monthly usage</th><th scope="col">Account status</th></tr></thead>
          <tbody>{(d?.items ?? []).map((o) => (
            <tr key={o.id} className="clickable" aria-selected={o.id === sel} onClick={() => setSel(o.id)}>
              <td><button className="linkbtn" style={{ textDecoration: "none", fontWeight: 650 }} onClick={() => setSel(o.id)}>{o.name}</button></td>
              <td>{o.plan}</td><td className="num">{o.enabled_checks} of {o.total_checks}</td>
              <td className="num">{o.monthly_usage.toLocaleString("en-GB")}</td>
              <td><Pill tone={o.status}>{STATUS[o.status] ?? o.status}</Pill></td>
            </tr>))}
            {d && d.items.length === 0 && <tr><td colSpan={5} className="empty">No organisations</td></tr>}
          </tbody>
        </table></div></div>
      </div>
      {org && (
        <aside className="panel side" aria-labelledby="org-h">
          <div><h2 id="org-h" className="big">{org.name}</h2><div style={{ marginTop: 6 }}><Pill tone={org.status}>{STATUS[org.status] ?? org.status}</Pill></div></div>
          <div className="list">
            <div className="row"><Layers size={20} aria-hidden /><span className="grow">Plan</span><strong>{org.plan}</strong></div>
            <div className="row"><Users size={20} aria-hidden /><span className="grow">Members</span><strong>{org.members}</strong></div>
          </div>
          <div><h2>Capabilities</h2><div className="list">
            {org.capabilities.map((c) => { const I = CAP_ICON[c.key] ?? FileText; return (
              <div className="row" key={c.key}><I size={20} aria-hidden /><span className="grow">{c.label}</span>
                <Pill tone={c.enabled ? "good" : undefined}>{c.enabled ? "Enabled" : "Not enabled"}</Pill></div>); })}
          </div></div>
          <div>
            <div className="pagehead" style={{ alignItems: "baseline" }}><h2>Monthly usage</h2><span className="actions muted">{org.monthly_usage.toLocaleString("en-GB")} of {org.monthly_cap.toLocaleString("en-GB")}</span></div>
            <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={org.monthly_cap} aria-valuenow={org.monthly_usage} aria-label="Monthly usage">
              <span style={{ width: `${Math.min(100, (100 * org.monthly_usage) / Math.max(org.monthly_cap, 1))}%` }} /></div>
          </div>
          <div><h2>Recent administration</h2>
            {activity.length === 0 ? <p className="muted">None yet</p> : (
              <ul className="timeline">{activity.slice(0, 5).map((a, i) => <li key={i}><div>{ACTION[a.action] ?? a.action}</div><div className="when">{ago(a.at)}</div></li>)}</ul>)}
          </div>
        </aside>
      )}
    </main>
  );
}
