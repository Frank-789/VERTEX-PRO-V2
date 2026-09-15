'use client'

import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Square } from 'lucide-react'

/**
 * 输入框。
 *
 * 快捷键：
 *   Enter        发送
 *   Shift+Enter  换行
 *   Esc          停止生成
 *
 * 高度随内容自增，上限 200px 后内部滚动 —— 长问题不被裁掉，
 * 又不会把对话挤没。
 */

const MAX_HEIGHT = 200

export function Composer({
  onSend,
  onStop,
  streaming = false,
  disabled = false,
  placeholder = '说清楚你想卖什么，我来跑数据',
  autoFocus = false,
}: {
  onSend: (text: string) => void
  onStop?: () => void
  streaming?: boolean
  disabled?: boolean
  placeholder?: string
  autoFocus?: boolean
}) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  // 高度自适应
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`
  }, [value])

  useEffect(() => {
    if (autoFocus) ref.current?.focus()
  }, [autoFocus])

  function submit() {
    const text = value.trim()
    if (!text || streaming || disabled) return
    onSend(text)
    setValue('')
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
      return
    }
    if (e.key === 'Escape' && streaming) {
      e.preventDefault()
      onStop?.()
    }
  }

  const canSend = value.trim().length > 0 && !streaming && !disabled

  return (
    <div className="border-t border-[var(--border)] bg-[var(--background)] px-4 pt-3 pb-4">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-[var(--radius-lg)] border border-[var(--input)] bg-[var(--card)] px-3 py-2 transition-colors focus-within:border-[var(--primary)]">
          <textarea
            ref={ref}
            rows={1}
            value={value}
            disabled={disabled}
            placeholder={placeholder}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="min-h-[26px] flex-1 resize-none bg-transparent py-1 text-[14.5px] leading-relaxed text-[var(--foreground)] outline-none focus-visible:outline-none placeholder:text-[var(--foreground-ghost)] disabled:opacity-50"
            aria-label="输入消息"
          />

          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)] border border-[var(--input)] text-[var(--foreground-soft)] transition-colors hover:border-[var(--destructive)] hover:text-[var(--destructive)]"
              aria-label="停止生成"
            >
              <Square size={13} fill="currentColor" />
            </button>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={!canSend}
              className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] text-white transition-opacity disabled:opacity-25"
              aria-label="发送"
            >
              <ArrowUp size={15} strokeWidth={2.5} />
            </button>
          )}
        </div>

        <p className="mt-1.5 px-1 text-[11px] text-[var(--foreground-ghost)]">
          Enter 发送 · Shift+Enter 换行
          {streaming && ' · Esc 停止'}
        </p>
      </div>
    </div>
  )
}
