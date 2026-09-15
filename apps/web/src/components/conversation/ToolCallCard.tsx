'use client'

import { useState } from 'react'
import { Check, ChevronRight, Loader2, X } from 'lucide-react'
import { DATA_SOURCE_LABEL, type ToolCall } from '@/lib/types'

/**
 * 工具调用卡片。
 *
 * 折叠时只给一行：状态图标 + 工具名 + 摘要（命中条数 / 耗时）。
 * 点开才展示细节。默认折叠 —— 采集过程不该盖过结论本身。
 */

const STATUS_ICON = {
  running: Loader2,
  ok: Check,
  failed: X,
} as const

const STATUS_CLASS = {
  running: 'text-[var(--primary)]',
  ok: 'text-[var(--success)]',
  failed: 'text-[var(--destructive)]',
} as const

function summarise(call: ToolCall): string {
  const bits: string[] = []
  if (call.status === 'running') bits.push('进行中')
  if (typeof call.count === 'number') bits.push(`${call.count} 条`)
  if (call.error) bits.push(call.error)
  if (typeof call.durationMs === 'number') {
    bits.push(call.durationMs >= 1000 ? `${(call.durationMs / 1000).toFixed(1)}s` : `${call.durationMs}ms`)
  }
  return bits.join(' · ')
}

export function ToolCallCard({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false)
  const Icon = STATUS_ICON[call.status]
  const expandable = Boolean(call.detail) || Boolean(call.error)
  const summary = summarise(call)

  return (
    <div className="my-1.5 overflow-hidden rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--secondary)]">
      <button
        type="button"
        disabled={!expandable}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={expandable ? open : undefined}
        className="flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors enabled:hover:bg-[var(--card)] disabled:cursor-default"
      >
        <Icon
          size={14}
          className={`shrink-0 ${STATUS_CLASS[call.status]} ${call.status === 'running' ? 'animate-spin' : ''}`}
          aria-hidden
        />
        <span className="shrink-0 text-[13px] font-medium text-[var(--foreground)]">{call.label}</span>

        {call.source && (
          <span className="shrink-0 rounded-[var(--radius-sm)] border border-[var(--border)] px-1.5 py-px text-[11px] text-[var(--foreground-faint)]">
            {DATA_SOURCE_LABEL[call.source]}
          </span>
        )}

        <span className="mono min-w-0 flex-1 truncate text-[11px] text-[var(--foreground-faint)]">
          {call.name}
        </span>

        {summary && (
          <span className="tnum shrink-0 text-[11px] text-[var(--foreground-soft)]">{summary}</span>
        )}

        {expandable && (
          <ChevronRight
            size={13}
            className={`shrink-0 text-[var(--foreground-ghost)] transition-transform duration-[var(--motion-fast)] ${
              open ? 'rotate-90' : ''
            }`}
            aria-hidden
          />
        )}
      </button>

      {open && expandable && (
        <div className="anim-disclose border-t border-[var(--border)] px-3 py-2">
          {call.error ? (
            <p className="text-[12px] text-[var(--destructive)]">{call.error}</p>
          ) : (
            <pre className="mono max-h-56 overflow-auto whitespace-pre-wrap break-all text-[11.5px] leading-relaxed text-[var(--foreground-soft)]">
              {call.detail}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
