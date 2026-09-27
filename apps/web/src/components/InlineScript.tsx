/**
 * 内联脚本。
 *
 * `type` 在服务端是 `text/javascript`（浏览器会**同步执行**，正好赶在首帧前），
 * 在客户端是 `text/plain`（浏览器忽略，不重复执行）——
 * 后者同时消掉 React 开发模式下对「渲染出 <script> 标签」的告警。
 *
 * 这个写法来自本版 Next.js 的官方文档
 * `node_modules/next/dist/docs/01-app/02-guides/preventing-flash-before-hydration.md`。
 *
 * 注意：严格的 CSP（不允许 'unsafe-inline'）会拦掉它，届时需要改用 nonce。
 */
export function InlineScript({ html }: { html: string }) {
  return (
    <script
      type={typeof window === 'undefined' ? 'text/javascript' : 'text/plain'}
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
