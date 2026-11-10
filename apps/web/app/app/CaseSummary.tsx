"use client";

import { Camera, IdCard, Mail, ScanFace, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Pill } from "@/components/ui";
import { con, type Session } from "@/lib/console";
import { CHECK_LABEL, REASON_TEXT, RESULT_LABEL, RESULT_TONE } from "@/lib/labels";

const ICON = { government_id: IdCard, face_match: ScanFace, liveness: ShieldCheck, email: Mail, phone: Mail } as Record<string, typeof IdCard>;

export function CheckList({ s }: { s: Session }) {
  return (
    <div className="list">
      {s.checks.map((c) => {
        const I = ICON[c.type] ?? ShieldCheck;
        return (
          <div className="row" key={c.id}>
            <I size={20} aria-hidden strokeWidth={1.7} />
            <span className="grow">{CHECK_LABEL[c.type] ?? c.type}</span>
            <Pill tone={RESULT_TONE[c.result]}>{c.type === "email" && c.result === "pass" ? "Confirmed" : RESULT_LABEL[c.result] ?? c.result}</Pill>
          </div>
        );
      })}
    </div>
  );
}

export function summaryText(s: Session): string | null {
  const reasons = [...new Set(s.checks.flatMap((c) => (c.result === "pass" ? [] : c.reasons)))].filter((r) => REASON_TEXT[r]);
  return reasons.length ? reasons.map((r) => REASON_TEXT[r]).join(" ") : null;
}

export default function CaseSummary({ id, onChange }: { id: string; onChange: () => void }) {
  const [s, setS] = useState<Session | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { setS(null); con<Session>(`/verifications/${id}`).then(setS).catch(() => setError("Not found.")); }, [id]);
  if (error) return <aside className="panel side"><p>{error}</p></aside>;
  if (!s) return <aside className="panel side"><p className="muted">Loading</p></aside>;
  const summary = summaryText(s);

  async function retry() {
    setError("");
    try {
      const tl = await con<{ review: { id: string; status: string; lock_version: number; assignee: string | null } | null }>(`/verifications/${s!.id}/timeline`);
      if (!tl.review) throw new Error("No open review.");
      const claimed = tl.review.status === "claimed" ? tl.review : await con<{ lock_version: number }>(`/reviews/${tl.review.id}/claim`, {});
      await con(`/reviews/${tl.review.id}/decision`, {
        expected_revision: s!.revision, outcome: "action_required", method: "evidence_review",
        reason: "Retry requested by reviewer", evidence_ids: s!.checks.filter((c) => !c.id.startsWith("chk_pending")).map((c) => c.id).slice(0, 1),
        lock_version: claimed.lock_version,
      });
      onChange();
      setS(await con<Session>(`/verifications/${s!.id}`));
    } catch (e) { setError((e as Error).message); }
  }

  return (
    <aside className="panel side" aria-labelledby="case-h">
      <div>
        <h2 id="case-h" className="big">{s.external_reference}</h2>
        <span className="muted">Case {s.id.slice(-8).toUpperCase()}</span>
      </div>
      <div><h2>Checks</h2><CheckList s={s} /></div>
      <div className="thumbs">
        <div><div className="thumb"><IdCard size={28} aria-hidden /></div><div className="cap">ID document</div></div>
        <div><div className="thumb"><Camera size={28} aria-hidden /></div><div className="cap">Selfie</div></div>
      </div>
      {summary && <div className="note"><strong>Review summary</strong>{summary}</div>}
      {error && <p className="error-summary" role="alert">{error}</p>}
      <div className="btnrow">
        <Link className="btn" href={`/app/cases/${s.id}`}>Review evidence</Link>
        <button className="btn secondary" onClick={retry} disabled={s.state !== "review_required"}>Request retry</button>
      </div>
    </aside>
  );
}
