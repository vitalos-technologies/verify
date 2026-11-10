"use client";

import { BarChart3, ClipboardList, ShieldCheck } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Shell } from "@/components/ui";
import StepUpDialog from "./StepUpDialog";
import { con } from "@/lib/console";

function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const params = useSearchParams();
  const [me, setMe] = useState<{ tenant_name: string; role: string; permissions: string[] } | null>(null);
  const [queue, setQueue] = useState(0);
  const [q, setQ] = useState(params.get("q") ?? "");
  useEffect(() => {
    if (path === "/app/login" || path === "/app/mfa") return;
    con<typeof me>("/me").then(setMe).catch(() => {});
    con<{ review_queue: number }>("/stats").then((s) => setQueue(s.review_queue)).catch(() => {});
  }, [path]);
  if (path === "/app/login" || path === "/app/mfa") return <>{children}</>;
  const nav = [
    { href: "/app", label: "Verifications", icon: ShieldCheck },
    { href: "/app/reviews", label: "Review queue", icon: ClipboardList, badge: queue },
    ...(me?.permissions.includes("billing:manage") ? [{ href: "/app/usage", label: "Usage & billing", icon: BarChart3 }] : []),
  ];
  const current = path.startsWith("/app/cases") ? "/app" : path;
  const page = nav.find((n) => n.href === current)?.label ?? "Case";
  return (
    <Shell title={me?.tenant_name ?? "Workspace"} nav={nav} current={current}
      crumbs={<><span>Workspace</span><span aria-hidden="true">/</span><strong>{page}</strong></>}
      user={me ? { name: me.role.charAt(0).toUpperCase() + me.role.slice(1), detail: me.tenant_name } : null}
      search={current === "/app" ? (
        <form className="search" role="search" onSubmit={(e) => { e.preventDefault(); router.replace(q ? `/app?q=${encodeURIComponent(q)}` : "/app"); }}>
          <label htmlFor="q" className="sr-only">Search verifications</label>
          <input id="q" placeholder="Search verifications…" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
      ) : null}>
      {children}
      <StepUpDialog />
    </Shell>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return <Suspense><WorkspaceShell>{children}</WorkspaceShell></Suspense>;
}
