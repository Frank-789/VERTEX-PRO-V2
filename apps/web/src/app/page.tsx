'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ArrowRight, ArrowUp } from 'lucide-react'
import { LANDING_EXAMPLES } from '@/lib/landing-examples'

/**
 * 首页。
 *
 * 一个输入框 + 四张示例卡片。没有 hero 大图、没有功能介绍段落 ——
 * 用户来这里是要提问的，不是来读文案的。示例卡片承担「告诉你能干什么」
 * 的职责，但方式是让用户直接点走，而不是解释。
 */
export default function Home() {
  const router = useRouter()
  const [value, setValue] = useState('')

  function go(text: string) {
    const q = text.trim()
    if (!q) return
    router.push(`/chat?q=${encodeURIComponent(q)}`)
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col justify-center px-6 py-16">
      <header className="mb-9">
        <h1 className="text-[26px] font-semibold tracking-tight text-[var(--foreground)]">
          Vertex
        </h1>
        <p className="mt-1.5 text-[14px] text-[var(--foreground-soft)]">
          说清楚你想卖什么，我来跑数据、出分析、做图。
        </p>
      </header>

      <div className="flex items-end gap-2 rounded-[var(--radius-lg)] border border-[var(--input)] bg-[var(--card)] px-3.5 py-2.5 transition-colors focus-within:border-[var(--primary)]">
        <textarea
          rows={1}
          value={value}
          placeholder="例如：我想做露营装备，预算 3 万，帮我看看能不能进场"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              go(value)
            }
          }}
          className="min-h-[30px] flex-1 resize-none bg-transparent py-1 text-[15px] leading-relaxed text-[var(--foreground)] outline-none focus-visible:outline-none placeholder:text-[var(--foreground-ghost)]"
          aria-label="描述你的经营问题"
        />
        <button
          type="button"
          onClick={() => go(value)}
          disabled={!value.trim()}
          className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] text-white transition-opacity disabled:opacity-25"
          aria-label="开始"
        >
          <ArrowUp size={15} strokeWidth={2.5} />
        </button>
      </div>

      <div className="mt-8 grid gap-2.5 sm:grid-cols-2">
        {LANDING_EXAMPLES.map((ex) => (
          <button
            key={ex.id}
            type="button"
            onClick={() => go(ex.prompt)}
            className="group rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--card)] px-3.5 py-3 text-left transition-colors hover:border-[var(--input)]"
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
    </main>
  )
}
