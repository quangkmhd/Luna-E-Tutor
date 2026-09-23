import type { NextConfig } from "next";

// Backend: cùng Docker bridge network → dùng container hostname
const BACKEND_HOST = process.env.BACKEND_HOST || process.env.VPS_HOST || 'http://backend';
const BACKEND_PORT = process.env.BACKEND_PORT || '8000';

// Voice & Talk: dùng network_mode: host → phải truy cập qua Docker host gateway
const VOICE_HOST = process.env.VOICE_HOST || process.env.VPS_HOST || 'http://host.docker.internal';
const VOICE_PORT = process.env.VOICE_PORT || '7860';
const TALK_HOST = process.env.TALK_HOST || process.env.VPS_HOST || 'http://host.docker.internal';
const TALK_PORT = process.env.TALK_PORT || '7863';

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/api/:path*",
        destination: `${BACKEND_HOST}:${BACKEND_PORT}/api/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${BACKEND_HOST}:${BACKEND_PORT}/api/:path*`,
      },
      {
        source: "/voice-bot/:path*",
        destination: `${VOICE_HOST}:${VOICE_PORT}/:path*`,
      },
      {
        source: "/talk-bot/:path*",
        destination: `${TALK_HOST}:${TALK_PORT}/:path*`,
      },
    ];
  },
};

export default nextConfig;
