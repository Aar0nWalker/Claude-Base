import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  turbopack: {
    root: '.',
  },
  // Rewrite proxy defaults to a 30s timeout — raise it if a backend route can
  // legitimately run long (e.g. a slow third-party fetch or heavy processing).
  experimental: {
    proxyTimeout: 120_000,
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    return [
      {
        source: '/backend/:path*',
        destination: `${backendUrl}/:path*`,
      },
    ]
  },
}

export default nextConfig
