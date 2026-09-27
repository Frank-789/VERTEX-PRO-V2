'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ArrowRight, ArrowUp } from 'lucide-react'
import { PaletteMenu } from '@/components/PaletteMenu'
import { LANDING_EXAMPLES } from '@/lib/landing-examples'
import {
  MAX_HEIGHT,
  MIN_HEIGHT,
  SHELL_SHADOW,
  SHELL_SHADOW_FOCUS,
} from '@/lib/surface'

/**
 * 首页。
 *
 * 一个输入框 + 四张示例卡片。没有 hero 大图、没有功能介绍段落 ——
 * 用户来这里是要提问的，不是来读文案的。示例卡片承担「告诉你能干什么」
 * 的职责，但方式是让用户直接点走，而不是解释。
 *
 * 提问框和对话页的输入框是**同一个东西的两种状态**，所以共用
 * `@/lib/surface` 里的阴影与高度规格 —— 从首页走到对话页，光标不该有落差。
 */
export default function Home() {
  const router = useRouter()
  const [value, setValue] = useState('')

  function go(text: string) {
    const q = text.trim()
    if (!q) return
    router.push(`/chat?q=${encodeURIComponent(q)}`)
  }

  const canSend = value.trim().length > 0

  return (
    <div className="flex min-h-dvh flex-col">
      <div className="flex shrink-0 justify-end px-3 py-2">
        <PaletteMenu />
      </div>

      <main className="mx-auto flex w-full max-w-[736px] flex-1 flex-col justify-center px-6 pb-20">
        <header className="mb-8">
          <h1 className="text-[26px] font-semibold tracking-tight text-[var(--foreground)]">
            Vertex
          </h1>
          <p className="mt-1.5 text-[14px] text-[var(--foreground-soft)]">
            说清楚你想卖什么，我来跑数据、出分析、做图。
          </p>
        </header>

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
            rows={1}
            name="q"
            value={value}
            placeholder="例如：我想做露营装备，预算 3 万，帮我看看能不能进场"
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              // isComposing：中文输入法选词时按 Enter 不该提交半成品
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                go(value)
              }
            }}
            className="block w-full resize-none border-0 bg-transparent p-1.5 text-[14px] leading-[21px] text-[var(--foreground)] focus-visible:outline-none placeholder:text-[var(--foreground-ghost)]"
            style={{ minHeight: MIN_HEIGHT, maxHeight: MAX_HEIGHT }}
            aria-label="描述你的经营问题"
          />

          <div className="flex min-h-8 items-end justify-between gap-2 px-0.5 pt-1">
            <span className="text-[11px] text-[var(--foreground-ghost)]">
              Enter 发送 · Shift+Enter 换行
            </span>

            <button
              type="button"
              onClick={() => go(value)}
              disabled={!canSend}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--foreground)] text-[var(--background)] transition-opacity hover:opacity-90 disabled:bg-[var(--muted)] disabled:text-[var(--muted-foreground)] disabled:opacity-55"
              aria-label="开始"
            >
              <ArrowUp size={17} strokeWidth={2.25} />
            </button>
          </div>
        </div>

        <div className="mt-7">
          <p className="mb-2.5 text-[11px] tracking-wide text-[var(--foreground-ghost)]">
            试试这些
          </p>
          <div className="grid gap-2.5 sm:grid-cols-2">
            {LANDING_EXAMPLES.map((ex) => (
              <button
                key={ex.id}
                type="button"
                onClick={() => go(ex.prompt)}
                className="group rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--card)] px-3.5 py-3 text-left transition-colors hover:border-[var(--input)]"
              >
                <span className="text-[11px] font-medium tracking-wide text-[var(--foreground-faint)]">
                  {ex.label}
                </span>
                <span className="mt-0.5 flex items-center justify-between gap-2">
                  <span className="text-[13.5px] font-medium text-[var(--foreground)]">
                    {ex.title}
                  </span>
                  <ArrowRight
                    size={13}
                    className="shrink-0 text-[var(--foreground-ghost)] transition-transform duration-[var(--motion-fast)] group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </span>
              </button>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
