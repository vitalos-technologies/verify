"use client";

import { Activity, Building2 } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Shell } from "@/components/ui";
import { plat } from "@/lib/platform";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [me, setMe] = useState<{ display_name: string; role: string } | null>(null);
  useEffect(() => { plat<{ display_name: string; role: string }>("/me").then(setMe).catch(() => {}); }, []);
  const admin = path.startsWith("/admin");
  const nav = [
    ...(me?.role === "platform_admin" ? [{ href: "/admin", label: "Organisations", icon: Building2 }] : []),
    { href: "/ops", label: "Service overview", icon: Activity },
  ];
  return (
    <Shell title={admin ? "Platform administration" : "Operations"} nav={nav} current={path}
      crumbs={<strong>{admin ? "Platform administration" : "Operations"}</strong>}
      user={me ? { name: me.display_name, detail: me.role === "platform_admin" ? "Platform admin" : "Operations" } : null}>
      {children}
    </Shell>
  );
}
