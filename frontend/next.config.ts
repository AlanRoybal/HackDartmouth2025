import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'picsum.photos',
        port: '',
        pathname: '/**',
      },
    ],
  },
  output: 'export',
  experimental: {
    allowedDevOrigins: ["9003-idx-studio-1745682676222.cluster-ux5mmlia3zhhask7riihruxydo.cloudworkstations.dev"],
  },
};

export default nextConfig;
