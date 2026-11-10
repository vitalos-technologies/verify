"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ago, Pill } from "@/components/ui";
import { con, type Review } from "@/lib/console";

const STATUS: Record<string, [string, string | undefined]> = { open: ["Open", "warn"], claimed: ["Claimed", undefined], awaiting_second_review: ["Second review", "warn"] };

export default function Reviews() {
  const router = useRouter();
  const [items, setItems] = useState<Review[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { con<{ items: Review[] }>("/reviews").then((r) => setItems(r.items)).catch(() => setItems([])); }, []);
  async function claim(r: Review) {
    try { await con(`/reviews/${r.id}/claim`, {}); router.push(`/app/cases/${r.session_id}`); } catch (e) { setError((e as Error).message); }
  }
  return (
    <main className="page">
      <div className="pagehead"><div><h1>Review queue</h1><p className="sub">Oldest first.</p></div></div>
      {error && <p className="error-summary" role="alert">{error}</p>}
      <div className="panel flush">
        {items === null ? <p className="empty">Loading</p> : items.length === 0 ? <p className="empty">Queue empty</p> : (
          <div className="tablewrap"><table>
            <thead><tr><th scope="col">Case</th><th scope="col">Status</th><th scope="col">Waiting</th><th scope="col"><span className="sr-only">Action</span></th></tr></thead>
            <tbody>{items.map((r) => (
              <tr key={r.id}>
                <td><Link className="ref" href={`/app/cases/${r.session_id}`}>{r.session_id.slice(-8).toUpperCase()}</Link></td>
                <td><Pill tone={STATUS[r.status]?.[1]}>{STATUS[r.status]?.[0] ?? r.status}</Pill></td>
                <td>{ago(r.created_at)}</td>
                <td style={{ textAlign: "right" }}>{r.status === "open" && <button className="btn" onClick={() => claim(r)}>Claim</button>}</td>
              </tr>))}
            </tbody>
          </table></div>
        )}
      </div>
    </main>
  );
}
