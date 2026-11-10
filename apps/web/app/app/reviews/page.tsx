"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { con, type Review, when } from "@/lib/console";

const STATUS: Record<string, string> = { open: "Open", claimed: "Claimed", awaiting_second_review: "Second review" };

export default function Reviews() {
  const router = useRouter();
  const [items, setItems] = useState<Review[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { con<{ items: Review[] }>("/reviews").then((r) => setItems(r.items)).catch(() => setItems([])); }, []);

  async function claim(r: Review) {
    try { await con(`/reviews/${r.id}/claim`, {}); router.push(`/app/cases/${r.session_id}`); }
    catch (e) { setError((e as Error).message); }
  }

  return (
    <main>
      <h1>Reviews</h1>
      {error && <p className="error-summary" role="alert">{error}</p>}
      {items === null ? <p className="muted">Loading</p> : items.length === 0 ? <p className="muted">Queue empty</p> : (
        <div className="scroll">
          <table>
            <thead><tr><th scope="col">Case</th><th scope="col">Status</th><th scope="col">Waiting since</th><th scope="col"><span className="sr-only">Action</span></th></tr></thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td><Link href={`/app/cases/${r.session_id}`}>{r.session_id.slice(-8)}</Link></td>
                  <td>{STATUS[r.status] ?? r.status}</td>
                  <td>{when(r.created_at)}</td>
                  <td>{r.status === "open" && <button className="btn inline" onClick={() => claim(r)}>Claim</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
