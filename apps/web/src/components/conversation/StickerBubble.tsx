'use client'

import { useState } from 'react'

/**
 * 表情包渲染。
 *
 * 表情刻意做得比正文大、无气泡背景、无描边无圆角 —— 让它读起来是「表情」
 * 而不是「图片附件」。加了框和底就变成插图了，语气全丢。
 *
 * 尺寸上限 160px：比正文大得多，但不至于把整屏占掉。
 * 加载失败时退化成一段文字，不让排版塌掉。
 */
export function StickerBubble({ src, alt }: { src: string; alt: string }) {
  const [broken, setBroken] = useState(false)

  if (broken) {
    return (
      <span className="text-[13px] text-[var(--foreground-faint)]">[表情: {alt}]</span>
    )
  }

  return (
    <span className="anim-sticker my-1 inline-block">
      {/* 表情是装饰性内容，alt 交给周围的文字承担语义 */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        width={160}
        height={160}
        loading="lazy"
        onError={() => setBroken(true)}
        className="select-none align-middle"
        draggable={false}
        style={{ width: 'auto', height: 'auto', maxWidth: 'min(160px, 100%)', maxHeight: 320 }}
      />
    </span>
  )
}
