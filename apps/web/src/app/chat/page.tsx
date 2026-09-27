'use client'

import { Suspense, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { ArrowLeft, RotateCcw } from 'lucide-react'
import { Composer } from '@/components/conversation/Composer'
import { ConversationTranscript } from '@/components/conversation/ConversationTranscript'
import { PaletteMenu } from '@/components/PaletteMenu'
import { MEASURE_PADDING } from '@/lib/surface'
import { useChat } from '@/lib/useChat'

function ChatSurface() {
  const params = useSearchParams()
  const initial = params.get('q') ?? ''
  const { messages, streaming, error, send, stop, reset } = useChat()
  const bootstrapped = useRef(false)

  // URL 带 ?q= 时自动发第一条，实现「首页输入 → 直接开跑」
  useEffect(() => {
    if (initial && !bootstrapped.current) {
      bootstrapped.current = true
      void send(initial)
    }
  }, [initial, send])

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex shrink-0 items-center gap-3 border-b border-[var(--border)] px-4 py-2.5">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-[12.5px] text-[var(--foreground-soft)] transition-colors hover:text-[var(--foreground)]"
        >
          <ArrowLeft size={14} aria-hidden />
          Vertex
        </Link>

        <div className="flex-1" />

        <PaletteMenu />

        {messages.length > 0 && (
          <button
            type="button"
            onClick={reset}
            className="flex items-center gap-1.5 text-[12.5px] text-[var(--foreground-faint)] transition-colors hover:text-[var(--foreground)]"
          >
            <RotateCcw size={13} aria-hidden />
            新对话
          </button>
        )}
      </header>

      <div className="min-h-0 flex-1">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center px-6">
            <p className="text-[13.5px] text-[var(--foreground-faint)]">
              描述你的经营问题，我来跑一遍完整流程。
            </p>
          </div>
        ) : (
          <ConversationTranscript messages={messages} />
        )}
      </div>

      {error && (
        <div
          role="alert"
          className={`mb-1 grid gap-1 rounded-[10px] border border-[color-mix(in_srgb,var(--destructive)_50%,var(--border))] p-3 text-[12px] text-[var(--destructive)] ${MEASURE_PADDING}`}
        >
          <strong className="font-semibold">没能继续</strong>
          <span>{error}</span>
        </div>
      )}

      <Composer onSend={send} onStop={stop} streaming={streaming} autoFocus={!initial} />
    </div>
  )
}

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatSurface />
    </Suspense>
  )
}
