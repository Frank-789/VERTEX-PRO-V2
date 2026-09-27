import type { Metadata, Viewport } from 'next'
import { InlineScript } from '@/components/InlineScript'
import { PALETTE_BOOTSTRAP } from '@/lib/palette'
import './globals.css'

export const metadata: Metadata = {
  title: 'Vertex · AI 电商经营智能体',
  description:
    '面向中小电商卖家的 AI 经营决策助手。多平台数据采集、五维选品分析、主图生成与售中监控。',
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#faf8f4' },
    { media: '(prefers-color-scheme: dark)', color: '#1b1917' },
  ],
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        {/* 在浏览器解析 HTML 时就同步执行，赶在首帧之前把色板打上，
            否则会先闪一下默认的纸白再跳成用户选的那个。 */}
        <InlineScript html={PALETTE_BOOTSTRAP} />
      </head>
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  )
}
