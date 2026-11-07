import type { NextConfig } from "next";

const API = process.env.DRONE_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    // mọi /api/* đi thẳng sang FastAPI (chỉ đọc results/), không có dữ liệu mẫu ở phía web
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
