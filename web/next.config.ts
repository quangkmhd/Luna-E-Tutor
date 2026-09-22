import type { NextConfig } from "next";

const VPS_HOST = process.env.VPS_HOST || 'http://127.0.0.1';
const BACKEND_PORT = process.env.BACKEND_PORT || '8000';
const VOICE_PORT = process.env.VOICE_PORT || '7860';
const TALK_PORT = process.env.TALK_PORT || '7863';

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/api/:path*",
        destination: `${VPS_HOST}:${BACKEND_PORT}/api/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${VPS_HOST}:${BACKEND_PORT}/api/:path*`,
      },
      {
        source: "/voice-bot/:path*",
        destination: `${VPS_HOST}:${VOICE_PORT}/:path*`,
      },
      {
        source: "/talk-bot/:path*",
        destination: `${VPS_HOST}:${TALK_PORT}/:path*`,
      },
    ];
  },
};

export default nextConfig;
