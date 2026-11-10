"use client";

import { use, useCallback, useEffect, useState } from "react";

import { CheckList, summaryText } from "../../CaseSummary";
import { Pill } from "@/components/ui";
import { con, LABEL, type Review, type Session, when } from "@/lib/console";
import { METHOD_LABEL, STATE_LABEL, STATE_TONE } from "@/lib/labels";

type Item = { at: string; kind: "decision" | "event"; type?: string; state?: string; revision?: number; outcome?: string; method?: string; actor_type?: string; reason_codes?: string[] };
type Timeline = { items: Item[]; review: (Review & { proposed_by?: string }) | null; appeal: { id: string; status: string; assignee: string | null } | null };

export default function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [s, setS] = useState<Session | null>(null);
  const [tl, setTl] = useState<Timeline | null>(null);
  const [me, setMe] = useState<string>("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [outcome, setOutcome] = useState("declined");
  const [method, setMethod] = useState("evidence_review");
  const [reason, setReason] = useState("");
  const [summary2, setSummary] = useState("");
  const [evidence, setEvidence] = useState<{ id: string; kind: string; available: boolean }[]>([]);
  const [why, setWhy] = useState("");
  const [shown, setShown] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const [sv, t, m] = await Promise.all([
      con<Session>(`/verifications/${id}`), con<Timeline>(`/verifications/${id}/timeline`), con<{ membership_id: string }>("/me"),
    ]);
    setS(sv); setTl(t); setMe(m.membership_id);
    setEvidence((await con<{ items: { id: string; kind: string; available: boolean }[] }>(`/verifications/${id}/evidence`)).items);
  }, [id]);
  useEffect(() => { load().catch(() => setError("Not found.")); }, [load]);

  async function act(fn: () => Promise<unknown>, done: string) {
    setError(""); setNote("");
    try { await fn(); setNote(done); setReason(""); await load(); } catch (e) { setError((e as Error).message); }
  }

  if (error && !s) return <main className="page"><h1>Case</h1><p role="alert">{error}</p></main>;
  if (!s || !tl) return <main className="page"><p className="muted">Loading</p></main>;

  const review = tl.review;
  const mine = review?.status === "claimed" && review.assignee === me;
  const checkIds = s.checks.filter((c) => !c.id.startsWith("chk_pending")).map((c) => c.id);
  const view = (eid: string) => act(async () => {
    const r = await con<{ download_path: string }>(`/evidence/${eid}/reveal`, { reason: why });
    setShown((x) => ({ ...x, [eid]: r.download_path }));
  }, "Access logged");
  const decide = () => act(() => con(`/reviews/${review!.id}/decision`, {
    expected_revision: s.revision, outcome, method, reason, evidence_ids: checkIds, lock_version: review!.lock_version,
  }), method === "alternative_method" && outcome === "approved" ? "Sent for second review" : "Decision recorded");
  const appeal = tl.appeal;

  const summary = summaryText(s);
  return (
    <main className="page split">
      <div className="col">
        <div>
          <div className="titlerow"><h1>{s.external_reference}</h1><Pill tone={STATE_TONE[s.state]}>{STATE_LABEL[s.state] ?? s.state}</Pill></div>
          <p className="sub">Case {s.id.slice(-8).toUpperCase()} · Policy {s.policy_id} v{s.policy_version} · {when(s.created_at)}</p>
        </div>
        <p className="sr-only" role="status" aria-live="polite">{note}</p>
        {note && <p className="banner">{note}</p>}
        {error && <p className="error-summary" role="alert">{error}</p>}
        <section className="panel" aria-labelledby="checks-h">
          <h2 id="checks-h">Checks</h2>
          <CheckList s={s} />
          {summary && <div className="note" style={{ marginTop: 12 }}><strong>Review summary</strong>{summary}</div>}
        </section>
        {evidence.length > 0 && (
          <section className="panel" aria-labelledby="ev-h">
            <h2 id="ev-h">Evidence</h2>
            {Object.keys(shown).length === 0 && evidence.some((e) => e.available) && (<>
              <label htmlFor="why">Reason for viewing</label>
              <input id="why" type="text" value={why} onChange={(e) => setWhy(e.target.value)} />
            </>)}
            <div className="thumbs" style={{ marginTop: 12 }}>
              {evidence.map((e) => (
                <div key={e.id}>
                  <div className="thumb">{!e.available ? <span>Deleted</span> : shown[e.id]
                    // eslint-disable-next-line @next/next/no-img-element
                    ? <img src={shown[e.id]} alt={e.kind === "selfie" ? "Selfie" : "Document"} />
                    : <button className="btn secondary" disabled={why.trim().length < 10} onClick={() => view(e.id)}>View</button>}</div>
                  <div className="cap">{e.kind === "selfie" ? "Selfie" : "ID document"}</div>
                </div>
              ))}
            </div>
          </section>
        )}
        <section className="panel" aria-labelledby="tl-h">
          <h2 id="tl-h">Timeline</h2>
          <ul className="timeline">
            {tl.items.map((i, n) => (
              <li key={n}>
                <div>{i.kind === "decision" ? `Decision: ${STATE_LABEL[i.outcome!] ?? i.outcome} (${METHOD_LABEL[i.method!] ?? i.method})` : (STATE_LABEL[i.state!] ?? i.state)}</div>
                <div className="when">{when(i.at)}</div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <aside className="panel side" aria-labelledby="act-h">
        <h2 id="act-h">Actions</h2>
        {!review && !["approved", "declined"].includes(s.state) && <p className="muted">Nothing to do</p>}
        {review?.status === "open" && <button className="btn block" onClick={() => act(() => con(`/reviews/${review.id}/claim`, {}), "Claimed")}>Claim</button>}
        {review?.status === "claimed" && !mine && <p className="muted">Claimed by another reviewer</p>}
        {review?.status === "awaiting_second_review" && (review.proposed_by === me
          ? <p className="muted">Waiting for a second reviewer</p>
          : (<>
            <p>Approve by alternative method?</p>
            <div className="btnrow">
              <button className="btn" onClick={() => act(() => con(`/reviews/${review.id}/second-review`, { confirm: true }), "Confirmed")}>Confirm</button>
              <button className="btn secondary" onClick={() => act(() => con(`/reviews/${review.id}/second-review`, { confirm: false }), "Returned to queue")}>Reject</button>
            </div>
          </>))}
        {mine && (<>
          <fieldset>
            <legend>Outcome</legend>
            {[["approved", "Approve"], ["declined", "Decline"], ["action_required", "Ask to retry"]].map(([v, l]) => (
              <label key={v} className="check" htmlFor={`o-${v}`}><input type="radio" id={`o-${v}`} name="outcome" checked={outcome === v} onChange={() => setOutcome(v)} /><span>{l}</span></label>
            ))}
          </fieldset>
          <fieldset>
            <legend>Method</legend>
            {[["evidence_review", "Evidence review"], ["alternative_method", "Alternative method"]].map(([v, l]) => (
              <label key={v} className="check" htmlFor={`m-${v}`}><input type="radio" id={`m-${v}`} name="method" checked={method === v} onChange={() => setMethod(v)} /><span>{l}</span></label>
            ))}
          </fieldset>
          <label htmlFor="reason">Reason</label>
          <textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          <button className="btn block" onClick={decide} disabled={reason.trim().length < 10}>Record decision</button>
        </>)}
        {["approved", "declined"].includes(s.state) && !appeal && (<>
          <label htmlFor="appeal">Record appeal</label>
          <textarea id="appeal" value={summary2} onChange={(e) => setSummary(e.target.value)} />
          <button className="btn secondary block" disabled={summary2.trim().length < 10}
            onClick={() => act(() => con(`/verifications/${s.id}/appeals`, { summary: summary2 }), "Appeal recorded")}>Record appeal</button>
        </>)}
        {appeal?.status === "open" && <button className="btn block" onClick={() => act(() => con(`/appeals/${appeal.id}/claim`, {}), "Appeal claimed")}>Claim appeal</button>}
        {appeal?.status === "claimed" && appeal.assignee === me && (<>
          <label htmlFor="ar">Appeal reason</label>
          <textarea id="ar" value={reason} onChange={(e) => setReason(e.target.value)} />
          <div className="btnrow">
            {[["approved", "Approve (alternative)", "alternative_method"], ["declined", "Uphold", "evidence_review"]].map(([o, l, m]) => (
              <button key={o} className={o === "approved" ? "btn" : "btn secondary"} disabled={reason.trim().length < 10}
                onClick={() => act(() => con(`/appeals/${appeal.id}/resolve`, { expected_revision: s.revision, outcome: o, method: m, reason, evidence_ids: checkIds }), "Appeal resolved")}>{l}</button>
            ))}
          </div>
        </>)}
      </aside>
    </main>
  );
}
