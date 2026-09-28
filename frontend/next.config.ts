import type { NextConfig } from "next";

// The API URL comes from NEXT_PUBLIC_API_URL (e.g. .env.local for local dev);
// lib/api.ts falls back to the deployed Render backend when it is unset.
const nextConfig: NextConfig = {
  reactCompiler: true,
  output: "export",
  // Static export has no image optimization server
  images: { unoptimized: true },
};

export default nextConfig;
