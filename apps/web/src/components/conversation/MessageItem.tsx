'use client'

import { memo } from 'react'
import { Check, Copy } from 'lucide-react'
import { useState } from 'react'
import { messageToPlainText, type Message } from '@/lib/types'
import { RichText } from './RichText'
import { ToolCallCard } from './ToolCallCard'

/**
 * 一条消息。
 *
 * 刻意不做左右分栏的气泡头像 —— 那是 IM 的语汇。
 * 这里是一个工作台：用户发言用左侧竖线标记，助手回复直接铺陈。
 * 长回答因此可以占满行宽，读起来像文档而不是聊天记录。
 */

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false)
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text)
          setDone(true)
          setTimeout(() => setDone(false), 1400)
        } catch {
          /* 剪贴板不可用时静默失败，不打断阅读 */
        }
      }}
      className="flex items-center gap-1 rounded-[var(--radius-sm)] px-1.5 py-1 text-[11px] text-[var(--foreground-ghost)] opacity-0 transition-opacity duration-[var(--motion-fast)] group-hover:opacity-100 focus-visible:opacity-100 hover:text-[var(--foreground-soft)]"
      aria-label={done ? '已复制' : '复制回答'}
    >
      {done ? <Check size={12} /> : <Copy size={12} />}
      {done ? '已复制' : '复制'}
    </button>
  )
}

export const MessageItem = memo(function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const plain = messageToPlainText(message)

  if (isUser) {
    return (
      <div className="anim-msg-in group flex gap-3 py-3">
        <div
          className="mt-0.5 w-[2px] shrink-0 self-stretch rounded-full bg-[var(--input)]"
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <div className="mb-1 text-[11px] font-medium tracking-wide text-[var(--foreground-faint)]">
            你
          </div>
          <div className="whitespace-pre-wrap break-words text-[14.5px] text-[var(--foreground)]">
            {plain}
          </div>
        </div>
        <CopyButton text={plain} />
      </div>
    )
  }

  return (
    <div className="anim-msg-in group flex gap-3 py-3">
      <div
        className="mt-0.5 w-[2px] shrink-0 self-stretch rounded-full bg-[var(--primary)] opacity-70"
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <div className="mb-1 text-[11px] font-medium tracking-wide text-[var(--foreground-faint)]">
          Vertex
        </div>

        {message.blocks.map((block, i) => {
          if (block.kind === 'tool') return <ToolCallCard key={i} call={block.call} />
          if (block.kind === 'sticker') {
            return <RichText key={i} text={`[[sticker/${block.file}]]`} />
          }
          return <RichText key={i} text={block.text} />
        })}

        {message.streaming && (
          <div className="mt-2 flex items-center gap-1.5" aria-label="正在输入">
            <span className="dot h-1.5 w-1.5 rounded-full bg-[var(--foreground-faint)]" />
            <span className="dot h-1.5 w-1.5 rounded-full bg-[var(--foreground-faint)]" />
            <span className="dot h-1.5 w-1.5 rounded-full bg-[var(--foreground-faint)]" />
          </div>
        )}
      </div>
      {!message.streaming && plain && <CopyButton text={plain} />}
    </div>
  )
})
