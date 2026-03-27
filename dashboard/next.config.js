/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    // missing in standard config
  },
  webpack: (config) => {
    // To handle optional dependencies of react-force-graph if needed
    return config;
  },
};

module.exports = nextConfig;
