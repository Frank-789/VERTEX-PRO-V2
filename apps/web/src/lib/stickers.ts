/**
 * 表情包。
 *
 * 模型在回复里写 `[[sticker/thinking.svg]]`，渲染时替换成表情图。
 * 这是纯约定的文本标记 —— 模型不需要额外的工具调用就能发表情。
 */

export const STICKER_DIR = '/stickers/vertex-default'

/** 匹配 `[[sticker/xxx.svg]]`，允许前后有空白。 */
const STICKER_RE = /\[\[\s*sticker\/([\w.-]+)\s*\]\]/g

export interface StickerHit {
  /** 文件名，如 thinking.svg */
  file: string
  /** 图片 URL */
  src: string
  /** 起止下标（用于切分文本） */
  start: number
  end: number
}

/** 找出文本里所有表情标记。 */
export function findStickers(text: string): StickerHit[] {
  const hits: StickerHit[] = []
  // 每次调用重置 lastIndex，避免正则的跨调用状态污染
  STICKER_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = STICKER_RE.exec(text)) !== null) {
    hits.push({
      file: m[1],
      src: `${STICKER_DIR}/${m[1]}`,
      start: m.index,
      end: m.index + m[0].length,
    })
  }
  return hits
}

/** 文本里是否含表情标记。 */
export function hasSticker(text: string): boolean {
  return findStickers(text).length > 0
}

type Segment =
  | { kind: 'text'; text: string }
  | { kind: 'sticker'; file: string; src: string }

/** 把一段文本按表情标记切成「文字 / 表情」交替的片段。 */
export function splitStickers(text: string): Segment[] {
  const hits = findStickers(text)
  if (hits.length === 0) return text ? [{ kind: 'text', text }] : []

  const out: Segment[] = []
  let cursor = 0
  for (const h of hits) {
    const before = text.slice(cursor, h.start)
    if (before) out.push({ kind: 'text', text: before })
    out.push({ kind: 'sticker', file: h.file, src: h.src })
    cursor = h.end
  }
  const after = text.slice(cursor)
  if (after) out.push({ kind: 'text', text: after })
  return out
}

/** 表情在正文里前后留白，且独占一行时更自然。 */
export function normalizeStickerSpacing(text: string): string {
  return text
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]+(\[\[\s*sticker\/)/g, '$1')
    .replace(/(\]\])[ \t]+/g, '$1')
}
