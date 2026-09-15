'use client'

import { useState } from 'react'

/**
 * 表情包渲染。
 *
 * 表情刻意做得比文字大、无气泡背景 —— 让它读起来是「表情」而不是「图片附件」。
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
        width={104}
        height={104}
        loading="lazy"
        onError={() => setBroken(true)}
        className="select-none align-middle"
        draggable={false}
      />
    </span>
  )
}
