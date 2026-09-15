'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { splitStickers } from '@/lib/stickers'
import { StickerBubble } from './StickerBubble'

/**
 * 正文渲染。
 *
 * 先把 `[[sticker/x.svg]]` 切成独立片段，再交给 markdown 渲染 ——
 * 这样表情永远不会被 markdown 当成普通文本吞掉。
 *
 * 样式上刻意不加边框和底色：这是对话正文，不是文档面板。
 * 层级靠字号和间距建立，不靠容器。
 */
export function RichText({ text }: { text: string }) {
  const segments = splitStickers(text)
  if (segments.length === 0) return null

  return (
    <>
      {segments.map((seg, i) =>
        seg.kind === 'sticker' ? (
          <StickerBubble key={i} src={seg.src} alt={seg.file.replace(/\.\w+$/, '')} />
        ) : (
          <div key={i} className="md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{seg.text}</ReactMarkdown>
          </div>
        ),
      )}
    </>
  )
}
