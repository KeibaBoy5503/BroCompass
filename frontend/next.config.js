/** @type {import('next').NextConfig} */
const nextConfig = {
  // 사진 분석은 AI 서버 응답이 느릴 수 있다. rewrite 프록시의 기본 대기시간(30초)을 늘린다.
  experimental: { proxyTimeout: 90_000 },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
