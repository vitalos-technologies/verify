import Link from "next/link";
import type { ComponentType, ReactNode } from "react";

type Icon = ComponentType<{ size?: number; "aria-hidden"?: boolean; strokeWidth?: number }>;

/** Logo kit mark: eye (Emerald 900 lid, Emerald 600 lower arc) with a check in the iris. */
export function Logo({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={(size * 40) / 64} viewBox="0 0 64 40" aria-hidden="true">
      <path d="M4 22C15 5 49 5 60 22" fill="none" stroke="#064e3b" strokeWidth="5" strokeLinecap="round" />
      <path d="M13 28C24 38 42 38 53 25" fill="none" stroke="#059669" strokeWidth="5" strokeLinecap="round" />
      <circle cx="32" cy="21" r="9.5" fill="#064e3b" />
      <path d="m27.3 21.2 3.2 3.2 6.2-6.6" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Brand({ href = "/" }: { href?: string }) {
  return <Link className="brand" href={href} aria-label="Vitalos Verify"><Logo /><span>Vitalos <span className="v">Verify</span></span></Link>;
}

const TONES: Record<string, string> = {
  approved: "good", verified: "good", pass: "good", passed: "good", confirmed: "good", active: "good", healthy: "good", enabled: "good",
  review_required: "warn", needs_review: "warn", attention: "warn", delayed: "warn", inconclusive: "warn", action_required: "warn", degraded: "warn",
  declined: "bad", fail: "bad", error: "bad", suspended: "bad", failed: "bad",
};

export function Pill({ tone, children }: { tone?: string; children: ReactNode }) {
  return <span className="pill" data-tone={tone ? TONES[tone] ?? tone : undefined}>{children}</span>;
}

export function Stat({ icon: I, label, value, tone }: { icon: Icon; label: string; value: ReactNode; tone?: "warn" }) {
  return (
    <div className={`stat${tone ? ` ${tone}` : ""}`}>
      <I size={28} aria-hidden strokeWidth={1.5} />
      <div><div className="label">{label}</div><div className="value num">{value}</div></div>
    </div>
  );
}

export type NavItem = { href: string; label: string; icon: Icon; badge?: number };

export function Shell({ title, crumbs, nav, current, user, search, children }: {
  title: string; crumbs: ReactNode; nav: NavItem[]; current: string; user?: { name: string; detail?: string } | null;
  search?: ReactNode; children: ReactNode;
}) {
  const initials = (user?.name ?? "?").split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase();
  return (
    <>
      <header className="topbar">
        <Brand href={nav[0]?.href ?? "/"} />
        <span className="divider" aria-hidden="true" />
        <div className="crumbs">{crumbs}</div>
        <span className="spacer" />
        {search}
        {user && <span className="avatar" aria-label={user.name}>{initials}</span>}
      </header>
      <div className="shell">
        <nav className="rail" aria-label={title}>
          <div className="title">{title}</div>
          {nav.map(({ href, label, icon: I, badge }) => (
            <Link key={href} href={href} aria-current={current === href ? "page" : undefined}>
              <I size={20} aria-hidden strokeWidth={1.7} /> {label}
              {badge ? <span className="badge" aria-label={`${badge} waiting`}>{badge}</span> : null}
            </Link>
          ))}
          {user && (
            <div className="foot">
              <div className="user"><span className="avatar">{initials}</span><span><strong>{user.name}</strong>{user.detail && <><br /><span className="muted">{user.detail}</span></>}</span></div>
            </div>
          )}
        </nav>
        {children}
      </div>
    </>
  );
}

export function Spark({ values, width = 170, height = 28 }: { values: (number | null)[]; width?: number; height?: number }) {
  const known = values.filter((v): v is number => v !== null);
  if (known.length < 2) return <span className="muted">Not enough data</span>;
  const pts = known;
  const min = Math.min(...pts, 95), max = 100;
  const step = width / Math.max(pts.length - 1, 1);
  const y = (v: number) => height - 2 - ((v - min) / Math.max(max - min, 0.01)) * (height - 4);
  const d = pts.map((v, i) => `${i ? "L" : "M"}${(i * step).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg className="spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <path d={`${d} L${width},${height} L0,${height}Z`} fill="var(--good-bg)" />
      <path d={d} fill="none" stroke="var(--good)" strokeWidth="1.6" />
    </svg>
  );
}

export const ago = (iso: string | null | undefined, now = Date.now()) => {
  if (!iso) return "—";
  const m = Math.max(0, Math.round((now - new Date(iso).getTime()) / 60000));
  return m < 1 ? "just now" : m < 60 ? `${m} minute${m === 1 ? "" : "s"} ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`;
};
