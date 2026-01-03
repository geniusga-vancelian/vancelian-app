/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: 'standalone', // Désactivé pour utiliser next start
  experimental: {
    instrumentationHook: true,
  },
}

module.exports = nextConfig
