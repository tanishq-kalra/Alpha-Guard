import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  output: "export",
  env: {
    NEXT_PUBLIC_API_URL: "https://alpha-guard-production.up.railway.app",
  },
};

export default nextConfig;