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
        // Report-only for now: nothing is blocked; what would be is logged to logs/csp-report.log (see src/lib/csp.ts).
        { key: "Content-Security-Policy-Report-Only", value: contentSecurityPolicy(process.env.NODE_ENV !== "production") },
      ],
    }];
  },
};

export default nextConfig;
