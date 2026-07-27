import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hide the Next.js "N" badge in local dev — not part of the product UI.
  devIndicators: false,
};

export default nextConfig;
