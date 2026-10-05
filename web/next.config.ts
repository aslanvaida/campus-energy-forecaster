import type { NextConfig } from "next";

// The Python model API (campus_energy_forecaster.api). The page calls /api/model/*, which is proxied here.
const MODEL_API_URL = process.env.MODEL_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/model/:path*", destination: `${MODEL_API_URL}/:path*` }];
  },
};

export default nextConfig;
