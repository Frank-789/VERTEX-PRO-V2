'use client'

import { useState } from 'react'
import { Check, ChevronRight, CircleAlert, LoaderCircle } from 'lucide-react'
import { DATA_SOURCE_LABEL, type ToolCall } from '@/lib/types'

/**
 * 工具调用。
 *
 * 版式学自 OpenAlice 的公开设计文档：**用内嵌导轨，不用嵌套卡片**。
 *
 * 卡片会引出「容器套容器」的观感 —— 对话里本来就有气泡、有表格、有代码块，
 * 再套一层边框就吵了。左边一条细导轨足以表达「这些是过程」，而且和正文的
 * 左缩进对齐得很好。
 *
 * 折叠时只给一行：状态图标 + 工具名 + 摘要。默认折叠 —— 采集过程不该盖过结论。
 *
 * 成功态刻意**不用绿色**：绿在这个产品里表示「盈利 / 安全」，
 * 拿它表示「工具跑通了」会把财务语义稀释掉。中性勾就够。
 */

const STATUS_ICON = {
  running: LoaderCircle,
  ok: Check,
  failed: CircleAlert,
} as const

function summarise(call: ToolCall): string {
  const bits: string[] = []
  if (call.status === 'running') bits.push('进行中')
  if (typeof call.count === 'number') bits.push(`${call.count} 条`)
  if (call.error) bits.push(call.error)
  if (typeof call.durationMs === 'number') {
    bits.push(
      call.durationMs >= 1000 ? `${(call.durationMs / 1000).toFixed(1)}s` : `${call.durationMs}ms`,
    )
  }
  return bits.join(' · ')
}

export function ToolCallCard({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false)
  const Icon = STATUS_ICON[call.status]
  const failed = call.status === 'failed'
  const expandable = Boolean(call.detail) || failed
  const summary = summarise(call)

  return (
    <div>
      <button
        type="button"
        disabled={!expandable}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={expandable ? open : undefined}
        className={`flex min-h-[34px] w-full items-center gap-2.5 text-left text-[12px] transition-colors enabled:hover:text-[var(--foreground)] disabled:cursor-default ${
          failed ? 'text-[var(--destructive)]' : 'text-[var(--muted-foreground)]'
        }`}
      >
        <Icon
          size={13}
          className={`shrink-0 ${
            call.status === 'running'
              ? 'text-[var(--primary)]'
              : failed
                ? 'text-[var(--destructive)]'
                : 'text-[var(--foreground-ghost)]'
          } ${call.status === 'running' ? 'animate-spin' : ''}`}
          aria-hidden
        />

        <span className="shrink-0 font-medium text-[var(--foreground)]">{call.label}</span>

        {call.source && (
          <span className="shrink-0 text-[11px] text-[var(--foreground-ghost)]">
            {DATA_SOURCE_LABEL[call.source]}
          </span>
        )}

        <span className="mono min-w-0 flex-1 truncate text-[11px] text-[var(--foreground-ghost)]">
          {call.name}
        </span>

        {summary && <span className="tnum shrink-0 text-[11px]">{summary}</span>}

        {expandable && (
          <ChevronRight
            size={13}
            className={`shrink-0 text-[var(--foreground-ghost)] transition-transform duration-[150ms] ${
              open ? 'rotate-90' : ''
            }`}
            aria-hidden
          />
        )}
      </button>

      {open && expandable && (
        <div className="anim-disclose mb-3 ml-[7px] border-l border-[var(--border)] pb-1 pl-[18px]">
          {failed ? (
            <p className="py-2 text-[12px] text-[var(--destructive)]">{call.error}</p>
          ) : (
            <pre className="mono max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-[var(--radius-md)] bg-[var(--secondary)] p-3 text-[12px] leading-relaxed text-[color-mix(in_srgb,var(--foreground)_88%,var(--muted-foreground))]">
              {call.detail}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
