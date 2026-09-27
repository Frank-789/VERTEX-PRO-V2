'use client'

import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Square } from 'lucide-react'
import {
  MAX_HEIGHT,
  MEASURE_PADDING,
  MIN_HEIGHT,
  SHELL_SHADOW,
  SHELL_SHADOW_FOCUS,
} from '@/lib/surface'

/**
 * 输入框。
 *
 * 快捷键：
 *   Enter        发送
 *   Shift+Enter  换行
 *   Esc          停止生成
 *
 * 版式学自 OpenAlice 的公开设计文档：
 *   · 外壳 26px 大圆角，**不描边**，用一圈极淡的阴影当边界 —— 描边会让它
 *     看起来像个表单，阴影才像个「可以往里放东西的托盘」
 *   · 聚焦反馈由外壳承担（focus-within 加深阴影），textarea 自身去掉 outline
 *   · 发送键是 32px 圆形，实心前景色 —— 和外壳的浅色形成足够对比
 *
 * 高度随内容自增，上限 168px 后内部滚动 —— 长问题不被裁掉，
 * 又不会把对话挤没。
 *
 * 阴影与高度来自 `@/lib/surface`，与首页的提问框同源 ——
 * 那两个是同一个东西的两种状态，不能各写一份。
 */

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

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(Math.max(el.scrollHeight, MIN_HEIGHT), MAX_HEIGHT)}px`
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
    // isComposing 是中文输入法的命门：不加这个判断，
    // 拼音选词时按 Enter 会把半成品直接发出去
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
    <div className={`shrink-0 pt-3 pb-5 ${MEASURE_PADDING}`}>
      <div
        className="rounded-[26px] bg-[color-mix(in_srgb,var(--card)_94%,transparent)] px-3 pt-3 pb-2.5 transition-shadow duration-[var(--motion-fast)] focus-within:shadow-[var(--shell-shadow-focus)]"
        style={
          {
            boxShadow: SHELL_SHADOW,
            '--shell-shadow-focus': SHELL_SHADOW_FOCUS,
          } as React.CSSProperties
        }
      >
        <textarea
          ref={ref}
          rows={1}
          name="message"
          value={value}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="block w-full resize-none border-0 bg-transparent p-1.5 text-[14px] leading-[21px] text-[var(--foreground)] focus-visible:outline-none placeholder:text-[var(--foreground-ghost)] disabled:opacity-50"
          style={{ minHeight: MIN_HEIGHT, maxHeight: MAX_HEIGHT }}
          aria-label="输入消息"
        />

        <div className="flex min-h-8 items-end justify-between gap-2 px-0.5 pt-1">
          <span className="text-[11px] text-[var(--foreground-ghost)]">
            Enter 发送 · Shift+Enter 换行
            {streaming && ' · Esc 停止'}
          </span>

          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--muted)] text-[var(--muted-foreground)] transition-opacity hover:opacity-80"
              aria-label="停止生成"
            >
              <Square size={13} fill="currentColor" />
            </button>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={!canSend}
              aria-busy={streaming}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--foreground)] text-[var(--background)] transition-opacity hover:opacity-90 disabled:bg-[var(--muted)] disabled:text-[var(--muted-foreground)] disabled:opacity-55"
              aria-label="发送"
            >
              <ArrowUp size={17} strokeWidth={2.25} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
