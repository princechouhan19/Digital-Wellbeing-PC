import type { NextConfig } from "next";

/**
 * Every previous host for the site redirects to the canonical one declared in
 * src/data/site.ts. 301, not 308, so search engines and the links in old
 * READMEs and release pages treat the canonical host as the permanent home.
 */
const CANONICAL_HOST = "digital-wellbeing-pc.vercel.app";
const RETIRED_HOSTS = ["digitalwellbeing.vercel.app", "notyourwellbeing.vercel.app"];

const nextConfig: NextConfig = {
  async redirects() {
    return RETIRED_HOSTS.map((value) => ({
      source: "/:path*",
      has: [
        {
          type: "host" as const,
          value,
        },
      ],
      destination: `https://${CANONICAL_HOST}/:path*`,
      statusCode: 301,
    }));
  },
};

export default nextConfig;
