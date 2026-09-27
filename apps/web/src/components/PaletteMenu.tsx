'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Check, SunMoon } from 'lucide-react'
import {
  PALETTES,
  applyPalette,
  readPalette,
  savePalette,
  type PaletteId,
} from '@/lib/palette'

/**
 * 色板切换器。
 *
 * 交互刻意做轻：一个图标按钮 + 下拉，选完即走，不弹面板不弹窗。
 * 换肤是个一次性动作，不该占用比它本身更多的注意力。
 *
 * 两条容易踩的坑：
 *   1. 首帧前必须由 <head> 里的内联脚本先把属性打上（见 layout.tsx），
 *      否则会闪一下默认色板。
 *   2. **开发模式下 React Strict Mode 会把 <html> 上的属性重置掉**
 *      （它只保留 JSX 里声明过的属性），内联脚本打的那个就没了。
 *      所以这里再用 useLayoutEffect 补一次 —— 生产构建下是 no-op。
 *      见 Next 文档 preventing-flash-before-hydration「Re-applying attributes in development」。
 */
export function PaletteMenu({ align = 'right' }: { align?: 'left' | 'right' }) {
  const [open, setOpen] = useState(false)
  // 初始值必须是 null（服务端渲染时的样子），否则会 hydration 不匹配。
  // 真正的值在下面 useLayoutEffect 里补上，早于绘制，看不见跳变。
  const [current, setCurrent] = useState<PaletteId | null>(null)
  const boxRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const saved = readPalette()
    setCurrent(saved)
    // 开发模式下内联脚本打的属性会被 Strict Mode 清掉，这里补回来
    applyPalette(saved)
  }, [])

  useEffect(() => {
    if (!open) return
    function onPointerDown(e: MouseEvent) {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function pick(id: PaletteId | null) {
    savePalette(id)
    setCurrent(id)
    setOpen(false)
  }

  const trigger = PALETTES.find((p) => p.id === current)

  return (
    <div className="relative" ref={boxRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="切换配色"
        className="flex items-center gap-1.5 rounded-[var(--radius-md)] px-1.5 py-1 text-[12.5px] text-[var(--foreground-faint)] transition-colors hover:text-[var(--foreground)]"
      >
        <SunMoon size={14} aria-hidden />
        <span className="hidden sm:inline">{trigger ? trigger.name : '跟随系统'}</span>
      </button>

      {open && (
        <div
          role="menu"
          className={`anim-disclose absolute top-full z-50 mt-1.5 w-44 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--card)] p-1 shadow-[0_8px_28px_color-mix(in_srgb,var(--foreground)_12%,transparent)] ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          <p className="px-2 pt-1.5 pb-1 text-[10.5px] tracking-wide text-[var(--foreground-ghost)]">
            配色
          </p>

          {PALETTES.map((p) => (
            <PaletteRow
              key={p.id}
              name={p.name}
              note={p.note}
              swatch={p.swatch}
              selected={current === p.id}
              onClick={() => pick(p.id)}
            />
          ))}

          <div className="my-1 h-px bg-[var(--border)]" />

          <PaletteRow
            name="跟随系统"
            note="由系统深浅色决定"
            selected={current === null}
            onClick={() => pick(null)}
          />
        </div>
      )}
    </div>
  )
}

function PaletteRow({
  name,
  note,
  swatch,
  selected,
  onClick,
}: {
  name: string
  note: string
  swatch?: { bg: string; primary: string }
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      role="menuitemradio"
      aria-checked={selected}
      onClick={onClick}
      className="flex w-full items-center gap-2.5 rounded-[var(--radius-sm)] px-2 py-1.5 text-left transition-colors hover:bg-[var(--secondary)]"
    >
      {/* 小圆点直接给出这个色板的底色与主色，比只写名字好认 */}
      {swatch ? (
        <span
          className="size-3.5 shrink-0 rounded-full border border-[color-mix(in_srgb,var(--foreground)_12%,transparent)]"
          style={{
            background: `linear-gradient(135deg, ${swatch.bg} 0 50%, ${swatch.primary} 50% 100%)`,
          }}
          aria-hidden
        />
      ) : (
        <span
          className="size-3.5 shrink-0 rounded-full border border-[var(--border)] bg-[linear-gradient(135deg,#faf8f4_0_50%,#1b1917_50%_100%)]"
          aria-hidden
        />
      )}

      <span className="min-w-0 flex-1">
        <span className="block text-[12.5px] leading-tight text-[var(--foreground)]">
          {name}
        </span>
        <span className="block text-[10.5px] leading-tight text-[var(--foreground-ghost)]">
          {note}
        </span>
      </span>

      {selected && (
        <Check size={13} className="shrink-0 text-[var(--primary)]" aria-hidden />
      )}
    </button>
  )
}
