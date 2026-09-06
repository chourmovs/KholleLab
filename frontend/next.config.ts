import type { NextConfig } from "next";

const internalApiUrl = process.env.INTERNAL_API_URL ?? "http://backend:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiUrl}/api/:path*`,
      },
    ];
  },
};
export default nextConfig;
