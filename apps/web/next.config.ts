import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for the demo image (docker/web.Dockerfile).
  output: "standalone",
};

export default nextConfig;
