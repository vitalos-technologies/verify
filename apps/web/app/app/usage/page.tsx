"use client";

import { BadgePercent, Mail, Receipt, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { Stat } from "@/components/ui";
import { con } from "@/lib/console";

type Line = { charge_type: string; quantity: number; amount_minor: number };
type Usage = { period: string; lines: Line[]; total_minor: number; invoice_id: string | null };
const gbp = (m: number) => (m / 100).toLocaleString("en-GB", { style: "currency", currency: "GBP" });
const LABEL: Record<string, string> = { completed_verification: "Completed verifications", message: "Messages", credit: "Credits" };

export default function UsagePage() {
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [u, setU] = useState<Usage | null>(null);
  useEffect(() => { setU(null); con<Usage>(`/usage?period=${period}`).then(setU).catch(() => {}); }, [period]);
  const line = (k: string) => u?.lines.find((l) => l.charge_type === k);
  return (
    <main className="page">
      <div className="pagehead">
        <div><h1>Usage &amp; billing</h1><p className="sub">Prices are pilot hypotheses.</p></div>
        <div className="actions"><label htmlFor="period" className="sr-only">Period</label>
          <input id="period" type="text" value={period} onChange={(e) => setPeriod(e.target.value)} style={{ width: 130 }} /></div>
      </div>
      <div className="stats">
        <Stat icon={ShieldCheck} label="Completed:" value={line("completed_verification")?.quantity ?? 0} />
        <Stat icon={Mail} label="Messages:" value={line("message")?.quantity ?? 0} />
        <Stat icon={BadgePercent} label="Credits:" value={gbp(-(line("credit")?.amount_minor ?? 0))} />
        <Stat icon={Receipt} label="Total:" value={u ? gbp(u.total_minor) : "–"} />
      </div>
      <div className="panel flush">
        <div className="tablewrap"><table>
          <thead><tr><th scope="col">Item</th><th scope="col">Quantity</th><th scope="col">Amount</th></tr></thead>
          <tbody>{(u?.lines ?? []).map((l) => (
            <tr key={l.charge_type}><td>{LABEL[l.charge_type] ?? l.charge_type}</td><td className="num">{l.quantity}</td><td className="num">{gbp(l.amount_minor)}</td></tr>
          ))}{u && u.lines.length === 0 && <tr><td colSpan={3} className="empty">No usage</td></tr>}</tbody>
        </table></div>
      </div>
    </main>
  );
}
