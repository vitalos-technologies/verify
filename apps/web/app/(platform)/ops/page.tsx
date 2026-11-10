"use client";

import { Clock, KeyRound, Layers, Trash2, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { Pill, Spark, Stat } from "@/components/ui";
import { plat } from "@/lib/platform";

type Ops = {
  environment: string; stats: { processing_now: number; delayed_jobs: number; open_incidents: number; deletions_due_today: number };
  queues: { key: string; label: string; pending: number; oldest_minutes: number | null; health: string }[];
  providers: { provider: string; label: string; success_rate: number | null; health: string; series: (number | null)[] }[];
  attention: { failed_webhooks: number; quarantined_events: number; error_sessions: number };
};
const mins = (m: number | null) => (m === null ? "—" : m < 1 ? "just now" : m < 60 ? `${Math.round(m)} minutes ago` : `${Math.round(m / 60)} h ago`);
const HEALTH: Record<string, string> = { healthy: "Healthy", delayed: "Delayed", degraded: "Degraded", no_data: "No data" };

export default function Operations() {
  const [d, setD] = useState<Ops | null>(null);
  useEffect(() => {
    const load = () => plat<Ops>("/operations").then(setD).catch(() => {});
    load(); const t = window.setInterval(load, 15000); return () => window.clearInterval(t);
  }, []);
  const att = d?.attention;
  return (
    <main className="page split">
      <div className="col">
        <div className="pagehead"><div>
          <div className="titlerow"><h1>Operations</h1>{d && <Pill tone={d.environment === "production" ? "good" : undefined}>{d.environment[0].toUpperCase() + d.environment.slice(1)}</Pill>}</div>
          <p className="sub">Monitor processing and resolve service issues.</p></div></div>
        <div className="stats">
          <Stat icon={Layers} label="Processing now:" value={d?.stats.processing_now ?? "–"} />
          <Stat icon={Clock} label="Delayed jobs:" value={d?.stats.delayed_jobs ?? "–"} />
          <Stat icon={TriangleAlert} label="Open incidents:" value={d?.stats.open_incidents ?? "–"} tone="warn" />
          <Stat icon={Trash2} label="Deletions due today:" value={d?.stats.deletions_due_today ?? "–"} />
        </div>
        <section className="panel flush" aria-labelledby="q-h"><h2 id="q-h">Processing queues</h2><div className="tablewrap"><table>
          <thead><tr><th scope="col">Queue</th><th scope="col">Pending</th><th scope="col">Oldest job</th><th scope="col">Health</th></tr></thead>
          <tbody>{(d?.queues ?? []).map((q) => (
            <tr key={q.key} aria-selected={q.health === "delayed"}><td><strong>{q.label}</strong></td><td className="num">{q.pending}</td>
              <td>{mins(q.oldest_minutes)}</td><td><Pill tone={q.health}>{HEALTH[q.health]}</Pill></td></tr>))}</tbody>
        </table></div></section>
        <section className="panel flush" aria-labelledby="p-h"><h2 id="p-h">Provider health</h2><div className="tablewrap"><table>
          <thead><tr><th scope="col">Provider</th><th scope="col">Health</th><th scope="col">30-day success</th><th scope="col">Trend (30 days)</th></tr></thead>
          <tbody>{(d?.providers ?? []).map((p) => (
            <tr key={p.provider}><td><strong>{p.label}</strong></td><td><Pill tone={p.health}>{HEALTH[p.health]}</Pill></td>
              <td className="num">{p.success_rate === null ? "—" : `${p.success_rate}%`}</td><td><Spark values={p.series} /></td></tr>))}</tbody>
        </table></div></section>
      </div>
      <div className="side">
        <aside className="panel side" aria-labelledby="inc-h">
          <h2 id="inc-h">Incidents</h2>
          <p className="muted">No open incidents</p>
          {att && (att.failed_webhooks + att.quarantined_events + att.error_sessions > 0) && (
            <div className="list">
              <div className="row"><span className="grow">Failed webhooks</span><strong className="num">{att.failed_webhooks}</strong></div>
              <div className="row"><span className="grow">Quarantined callbacks</span><strong className="num">{att.quarantined_events}</strong></div>
              <div className="row"><span className="grow">Sessions in provider error</span><strong className="num">{att.error_sessions}</strong></div>
            </div>)}
        </aside>
        <aside className="panel side" aria-labelledby="sa-h">
          <h2 id="sa-h">Support access</h2>
          <div className="list"><div className="row"><KeyRound size={20} aria-hidden /><span className="grow muted">No active grants</span></div></div>
        </aside>
      </div>
    </main>
  );
}
