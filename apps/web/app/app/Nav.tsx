"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { con } from "@/lib/console";

export default function Nav() {
  const path = usePathname();
  const [me, setMe] = useState<{ tenant_name: string; role: string } | null>(null);
  useEffect(() => { if (path !== "/app/login") con<{ tenant_name: string; role: string }>("/me").then(setMe).catch(() => {}); }, [path]);
  if (path === "/app/login") return null;
  const cur = (p: string) => (path === p ? "page" : undefined);
  return (
    <nav className="topbar" aria-label="Console">
      <strong>{me?.tenant_name ?? "Vitalos Verify"}</strong>
      <Link href="/app" aria-current={cur("/app")}>Verifications</Link>
      <Link href="/app/reviews" aria-current={cur("/app/reviews")}>Reviews</Link>
      {me && <span className="muted">{me.role}</span>}
    </nav>
  );
}
