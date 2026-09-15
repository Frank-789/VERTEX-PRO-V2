'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Message } from '@/lib/types'
import { MessageItem } from './MessageItem'

/**
 * 对话流。
 *
 * 自动吸底，但**仅在用户本就在底部时**才吸 —— 用户往上翻看历史时
 * 不该被新内容拽回去。翻走之后给一个「回到最新」的胶囊，而不是硬把他拽回来。
 *
 * 阅读宽度固定在 736px 并居中。这个尺度来自 OpenAlice 的公开设计文档，
 * 也是排版学上公认的舒适区间（约 45~75 个汉字/行）。行再长，眼睛回行会找错行。
 *
 * 内边距用 `max()` 而不是纯居中：窗口窄的时候保底 24px，
 * 窗口宽的时候才让出居中的余量。
 */

const NEAR_BOTTOM_PX = 72

export function ConversationTranscript({ messages }: { messages: Message[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollerRef = useRef<HTMLDivElement>(null)
  const pinnedRef = useRef(true)
  const [following, setFollowing] = useState(true)

  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    const onScroll = () => {
      const gap = el.scrollHeight - el.scrollTop - el.clientHeight
      const pinned = gap < NEAR_BOTTOM_PX
      pinnedRef.current = pinned
      setFollowing(pinned)
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (pinnedRef.current) {
      bottomRef.current?.scrollIntoView({ block: 'end' })
    }
  }, [messages])

  const jumpToLatest = useCallback(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    bottomRef.current?.scrollIntoView({
      block: 'end',
      behavior: reduce ? 'auto' : 'smooth',
    })
    pinnedRef.current = true
    setFollowing(true)
  }, [])

  return (
    <div className="relative h-full">
      <div
        ref={scrollerRef}
        className="h-full overflow-y-auto overflow-x-hidden [scrollbar-gutter:stable]"
      >
        <div className="flex flex-col gap-8 px-[max(24px,calc((100%-736px)/2))] pt-8">
          {messages.map((m, i) => (
            <MessageItem key={m.id} message={m} isLatest={i === messages.length - 1} />
          ))}
        </div>
        <div ref={bottomRef} className="h-8" />
      </div>

      {!following && messages.length > 0 && (
        <button
          type="button"
          onClick={jumpToLatest}
          className="absolute bottom-[92px] right-[max(18px,calc((100%-736px)/2))] rounded-full border border-[color-mix(in_srgb,var(--primary)_42%,var(--border))] bg-[color-mix(in_srgb,var(--secondary)_92%,transparent)] px-2.5 py-1.5 text-[11px] font-semibold text-[var(--foreground)] shadow-[0_5px_18px_rgba(0,0,0,0.08)] transition-colors hover:border-[var(--primary)]"
        >
          回到最新
        </button>
      )}
    </div>
  )
}
