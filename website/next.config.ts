import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // Redirect old domain to canonical production domain
      {
        source: '/:path*',
        has: [
          {
            type: 'host',
            value: 'notyourwellbeing.vercel.app',
          },
        ],
        destination: 'https://digitalwellbeing.vercel.app/:path*',
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
