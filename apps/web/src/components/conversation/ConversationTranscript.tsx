'use client'

import { useEffect, useRef } from 'react'
import type { Message } from '@/lib/types'
import { MessageItem } from './MessageItem'

/**
 * 对话流。
 *
 * 自动吸底，但仅在用户本就在底部时才吸 —— 用户往上翻看历史时
 * 不该被新内容拽回去。
 */
export function ConversationTranscript({ messages }: { messages: Message[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollerRef = useRef<HTMLDivElement>(null)
  const pinnedRef = useRef(true)

  // 记录用户是否停留在底部
  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    const onScroll = () => {
      const gap = el.scrollHeight - el.scrollTop - el.clientHeight
      pinnedRef.current = gap < 80
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (pinnedRef.current) {
      bottomRef.current?.scrollIntoView({ block: 'end' })
    }
  }, [messages])

  return (
    <div ref={scrollerRef} className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl divide-y divide-[var(--border)] px-4">
        {messages.map((m) => (
          <MessageItem key={m.id} message={m} />
        ))}
      </div>
      <div ref={bottomRef} className="h-6" />
    </div>
  )
}
