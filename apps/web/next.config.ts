import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    // Enable Server Actions & React 19 optimisations
  },
  transpilePackages: ['three'],
};

export default nextConfig;
