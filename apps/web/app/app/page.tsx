"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Chip from "./Chip";
import { con, type Session, when } from "@/lib/console";

const FILTERS: [string, string][] = [["", "All"], ["review_required", "Needs review"], ["approved", "Approved"], ["declined", "Declined"], ["in_progress", "In progress"]];

export default function Verifications() {
  const [state, setState] = useState("");
  const [items, setItems] = useState<Session[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);

  useEffect(() => {
    setItems(null);
    con<{ items: Session[]; next_cursor: string | null }>(`/verifications?limit=25${state ? `&state=${state}` : ""}`)
      .then((r) => { setItems(r.items); setCursor(r.next_cursor); }).catch(() => setItems([]));
  }, [state]);

  async function more() {
    const r = await con<{ items: Session[]; next_cursor: string | null }>(`/verifications?limit=25&cursor=${encodeURIComponent(cursor!)}${state ? `&state=${state}` : ""}`);
    setItems((x) => [...(x ?? []), ...r.items]);
    setCursor(r.next_cursor);
  }

  return (
    <main>
      <h1>Verifications</h1>
      <div className="tabs" role="group" aria-label="Filter">
        {FILTERS.map(([v, l]) => <button key={v} aria-pressed={state === v} onClick={() => setState(v)}>{l}</button>)}
      </div>
      {items === null ? <p className="muted">Loading</p> : items.length === 0 ? <p className="muted">None</p> : (
        <div className="scroll">
          <table>
            <thead><tr><th scope="col">Reference</th><th scope="col">Status</th><th scope="col">Created</th></tr></thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td><Link href={`/app/cases/${s.id}`}>{s.external_reference}</Link></td>
                  <td><Chip value={s.state} /></td>
                  <td>{when(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {cursor && <button className="btn secondary inline" onClick={more}>More</button>}
    </main>
  );
}
