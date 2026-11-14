import type { NextConfig } from "next";
import { contentSecurityPolicy } from "./src/lib/csp";

const nextConfig: NextConfig = {
  poweredByHeader: false,  // do not name the framework in every answer
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Frame-Options", value: "DENY" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "same-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        { key: "Cross-Origin-Opener-Policy", value: "same-origin-allow-popups" },  // signing in with Google opens a popup
        // Enforced since 14/11/2026 after report-only use left logs/csp-report.log empty; breaches are still logged there.
        // CSP_REPORT_ONLY=1 in .env.local goes back to report-only (nothing blocked) if signing in ever breaks.
        { key: process.env.CSP_REPORT_ONLY === "1" ? "Content-Security-Policy-Report-Only" : "Content-Security-Policy",
          value: contentSecurityPolicy(process.env.NODE_ENV !== "production") },
      ],
    }];
  },
};

export default nextConfig;
