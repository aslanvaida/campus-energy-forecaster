import type { NextConfig } from "next";

// The dashboard is static: it reads public/data/*.json, which the Python scripts write. It is exported as plain files so it
// can be hosted anywhere (GitHub Pages sets NEXT_PUBLIC_BASE_PATH to the repository name).
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
