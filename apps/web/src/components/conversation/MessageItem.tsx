'use client'

import { memo, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { messageToPlainText, type Block, type Message } from '@/lib/types'
import { RichText } from './RichText'
import { ToolCallCard } from './ToolCallCard'

/**
 * 一条消息。
 *
 * 版式学自 OpenAlice 的公开设计文档：
 *   · 用户发言 —— 右对齐的浅色气泡（20px 圆角，secondary 底色，最大 88% 宽）
 *   · 助手回复 —— 直接铺在画布上，无气泡无描边，占满阅读宽度
 *
 * 这个不对称是有意的：用户的话是「一句话」，助手的话是「一份东西」。
 * 两边都套气泡的话，长回答会被挤成窄条，读起来很累。
 *
 * 用户输入**不做 Markdown 渲染** —— 他打 `**粗体**` 就该原样看到那两个星号，
 * 而不是被悄悄变成粗体。
 */

function CopyButton({ text, alwaysVisible }: { text: string; alwaysVisible?: boolean }) {
  const [done, setDone] = useState(false)
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text)
          setDone(true)
          setTimeout(() => setDone(false), 2000)
        } catch {
          /* 剪贴板不可用时静默失败，不打断阅读 */
        }
      }}
      className={`flex items-center gap-1 rounded-[var(--radius-sm)] px-1.5 py-1 text-[11px] text-[var(--foreground-ghost)] transition-opacity duration-[var(--motion-fast)] hover:text-[var(--foreground-soft)] focus-visible:opacity-100 group-hover:opacity-100 ${
        alwaysVisible ? 'opacity-100' : 'opacity-0'
      }`}
      aria-label={done ? '已复制' : '复制'}
    >
      {done ? <Check size={12} /> : <Copy size={12} />}
      {done ? '已复制' : '复制'}
    </button>
  )
}

/** 助手回答里「过程性」的文字：退到后景，让最终结论跳出来。 */
function isProgressText(blocks: Block[], index: number): boolean {
  for (let i = index + 1; i < blocks.length; i++) {
    if (blocks[i].kind === 'text') return true
  }
  return false
}

export const MessageItem = memo(function MessageItem({
  message,
  isLatest,
}: {
  message: Message
  isLatest?: boolean
}) {
  const plain = messageToPlainText(message)

  if (message.role === 'user') {
    return (
      <article className="anim-msg-in group flex flex-col items-end">
        <div className="max-w-[min(88%,42rem)] rounded-[20px] bg-[var(--secondary)] px-4 py-3">
          <div className="whitespace-pre-wrap break-words text-[14px] leading-[1.62] text-[var(--foreground)]">
            {plain}
          </div>
        </div>
        <div className="mt-1.5 flex min-h-[28px] items-center">
          <CopyButton text={plain} alwaysVisible={isLatest} />
        </div>
      </article>
    )
  }

  return (
    <article className="anim-msg-in group flex flex-col">
      <div className="grid gap-5">
        {message.blocks.map((block, i) => {
          if (block.kind === 'tool') return <ToolCallCard key={i} call={block.call} />
          if (block.kind === 'sticker') {
            return <RichText key={i} text={`[[sticker/${block.file}]]`} />
          }
          return (
            <div
              key={i}
              className={
                isProgressText(message.blocks, i)
                  ? 'text-[color-mix(in_srgb,var(--foreground)_88%,var(--muted-foreground))]'
                  : undefined
              }
            >
              <RichText text={block.text} />
            </div>
          )
        })}
      </div>

      {message.streaming && (
        <div className="mt-3 flex items-center gap-1.5" aria-label="正在输入">
          <span className="dot h-1.5 w-1.5 rounded-full bg-[var(--foreground-faint)]" />
          <span className="dot h-1.5 w-1.5 rounded-full bg-[var(--foreground-faint)]" />
          <span className="dot h-1.5 w-1.5 rounded-full bg-[var(--foreground-faint)]" />
        </div>
      )}

      {!message.streaming && plain && (
        <div className="mt-1.5 flex min-h-[28px] items-center">
          <CopyButton text={plain} alwaysVisible={isLatest} />
        </div>
      )}
    </article>
  )
})
