/**
 * 色板注册表。
 *
 * 色板的**定义**在 `globals.css`（`:root[data-palette="..."]`），这里只登记
 * 「有哪些色板」和「怎么切换」。两边必须同时改 —— 加一个色板要动两个文件。
 *
 * 切换的实质就是在 `<html>` 上加/摘一个属性，CSS 变量随之整套换掉。
 * 之所以能这么轻，是因为 globals.css 里用的是 `@theme inline`
 * （见那个文件顶部的说明）。
 */

export type PaletteId = 'paper' | 'linen' | 'graphite' | 'midnight'

export const STORAGE_KEY = 'vertex:palette'

export interface PaletteDef {
  id: PaletteId
  name: string
  note: string
  /** 供菜单里画那个小圆点，取色板自己的底色和主色 */
  swatch: { bg: string; primary: string }
}

export const PALETTES: readonly PaletteDef[] = [
  {
    id: 'paper',
    name: '纸白',
    note: '暖白纸面，默认',
    swatch: { bg: '#faf8f4', primary: '#2f6fb5' },
  },
  {
    id: 'linen',
    name: '亚麻',
    note: '冷纸面，久看不累',
    swatch: { bg: '#f7f8f6', primary: '#2c6a72' },
  },
  {
    id: 'graphite',
    name: '石墨',
    note: '深色，中性灰',
    swatch: { bg: '#1b1917', primary: '#6ea6dc' },
  },
  {
    id: 'midnight',
    name: '午夜',
    note: '深色，偏蓝',
    swatch: { bg: '#14171c', primary: '#6f9fe8' },
  },
] as const

const IDS = PALETTES.map((p) => p.id)

function isPaletteId(v: unknown): v is PaletteId {
  return typeof v === 'string' && IDS.includes(v as PaletteId)
}

/** 读用户选的色板。返回 null 表示「跟随系统」。 */
export function readPalette(): PaletteId | null {
  if (typeof window === 'undefined') return null
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return isPaletteId(v) ? v : null
  } catch {
    // 隐私模式下 localStorage 会抛异常。读不到就当没选过。
    return null
  }
}

/** 应用色板。null = 跟随系统 —— 摘掉属性，把决定权交回 prefers-color-scheme。 */
export function applyPalette(id: PaletteId | null) {
  const root = document.documentElement
  if (id) root.setAttribute('data-palette', id)
  else root.removeAttribute('data-palette')
}

export function savePalette(id: PaletteId | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // 存不下就算了，本次会话内照样生效，不该因此报错
  }
  applyPalette(id)
}

/**
 * 首帧前执行的引导脚本，内联进 `<head>`。
 *
 * 浏览器解析到它时同步执行 —— 早于任何内容绘制，也早于 React 介入，
 * 所以用户不会看到「先纸白、后变石墨」的闪一下。
 *
 * 由注册表生成，避免手写字符串跟色板列表走散。
 */
export const PALETTE_BOOTSTRAP =
  `(function(){try{var v=localStorage.getItem(${JSON.stringify(STORAGE_KEY)});` +
  `if(${JSON.stringify(IDS)}.indexOf(v)>-1){document.documentElement.setAttribute("data-palette",v)}}catch(e){}})()`
