// Applicant surface. API calls are proxied same-origin so the HttpOnly applicant cookie
// (Path=/applicant, SameSite=Strict) works without exposing tokens to scripts.
const apiOrigin = process.env.VV_API_ORIGIN || "http://localhost:8000";
const devRoutes = process.env.VV_ENABLE_DUMMY_PROVIDER === "1";

const securityHeaders = [
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=()" },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      // Next.js inline bootstrap scripts; no third-party scripts or analytics on applicant pages.
      "script-src 'self' 'unsafe-inline'" + (process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""),
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data:",
      "connect-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'none'",
      "form-action 'self'",
    ].join("; "),
  },
  { key: "Cache-Control", value: "no-store" },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    const rules = [
      { source: "/applicant/:path*", destination: `${apiOrigin}/applicant/:path*` },
      { source: "/console/:path*", destination: `${apiOrigin}/console/:path*` },
    ];
    if (devRoutes) rules.push({ source: "/dummy-provider/:path*", destination: `${apiOrigin}/dummy-provider/:path*` });
    return rules;
  },
};

export default nextConfig;
