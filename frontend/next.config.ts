import type { NextConfig } from "next";

// Path prefix this Next app is served under (e.g. "/_dev" or "/_test"). Empty
// for prod (served at root). Set via NEXT_BASE_PATH on the frontend container;
// env_tools.py derives it from the profile. Next applies basePath to page
// routes and /_next/static/* assets — app-level fetches use NEXT_PUBLIC_API_URL
// which env_tools.py also prefixes per profile.
const basePath = process.env.NEXT_BASE_PATH || undefined;

const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: false,
  basePath,
};

export default nextConfig;
