import type { NextConfig } from 'next'

/**
 * 同源代理：浏览器只与本域通信，后端地址不出现在客户端。
 *
 * 这样做的收益：
 *  1. 消灭 CORS —— 不再需要在后端维护 ALLOWED_ORIGINS 白名单
 *  2. 后端地址不再硬编码进客户端 bundle
 *  3. 密钥全部留在服务端
 *  4. 未来加鉴权只需在中间件拦截
 */
const API_ORIGIN = process.env.API_ORIGIN ?? 'http://localhost:8000'

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${API_ORIGIN}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
