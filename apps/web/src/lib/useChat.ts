'use client'

import { useCallback, useRef, useState } from 'react'
import type { Block, Message, ToolCall } from './types'

/**
 * 对话状态与 SSE 流解析。
 *
 * 后端事件协议（沿用第一代，便于后端平滑迁移）：
 *   event: tool_call  data: {id, name, label, status, count, durationMs, error}
 *   event: chunk      data: {text}
 *   event: done       data: {}
 *   event: error      data: {message}
 *
 * 一条助手消息由「块」序列构成：文本块与工具块交替。
 * 收到工具事件就追加一个工具块，收到文本就并入末尾的文本块 ——
 * 这样工具调用可以出现在回答中间，而不是被挤到开头。
 */

const API_BASE = '/api/v1'

function uid(): string {
  return Math.random().toString(36).slice(2, 11)
}

function emptyAssistant(): Message {
  return { id: uid(), role: 'assistant', blocks: [], createdAt: Date.now(), streaming: true }
}

/** 把一段文本并入末尾文本块；末尾不是文本块就新开一个。 */
function appendText(blocks: Block[], text: string): Block[] {
  const last = blocks[blocks.length - 1]
  if (last?.kind === 'text') {
    const merged = [...blocks]
    merged[merged.length - 1] = { kind: 'text', text: last.text + text }
    return merged
  }
  return [...blocks, { kind: 'text', text }]
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStreaming(false)
    setMessages((prev) =>
      prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
    )
  }, [])

  const send = useCallback(
    async (text: string, platform?: string) => {
      const userMsg: Message = {
        id: uid(),
        role: 'user',
        blocks: [{ kind: 'text', text }],
        createdAt: Date.now(),
      }
      const assistant = emptyAssistant()
      setMessages((prev) => [...prev, userMsg, assistant])
      setStreaming(true)
      setError(null)

      const controller = new AbortController()
      abortRef.current = controller

      /** 就地更新正在流式的助手消息。 */
      const patch = (fn: (blocks: Block[]) => Block[]) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === assistant.id ? { ...m, blocks: fn(m.blocks) } : m)),
        )

      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, platform, stream: true }),
          signal: controller.signal,
        })

        if (!res.ok || !res.body) {
          throw new Error(`服务返回 ${res.status}`)
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        // 逐行解析 SSE —— 不依赖 EventSource，因为它不支持 POST
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          let eventName = ''
          for (const raw of lines) {
            const line = raw.trimEnd()
            if (!line) {
              eventName = ''
              continue
            }
            if (line.startsWith('event:')) {
              eventName = line.slice(6).trim()
              continue
            }
            if (!line.startsWith('data:')) continue

            const payload = line.slice(5).trim()
            if (payload === '[DONE]') continue

            let data: any
            try {
              data = JSON.parse(payload)
            } catch {
              continue
            }

            if (eventName === 'tool_call') {
              const call: ToolCall = {
                id: data.id ?? uid(),
                name: data.name ?? 'tool',
                label: data.label ?? data.name ?? '工具',
                status: data.status ?? 'running',
                source: data.source,
                count: data.count,
                durationMs: data.durationMs,
                error: data.error,
                detail: data.detail,
              }
              patch((blocks) => {
                const idx = blocks.findIndex((b) => b.kind === 'tool' && b.call.id === call.id)
                if (idx >= 0) {
                  const next = [...blocks]
                  const prev = next[idx] as Extract<Block, { kind: 'tool' }>
                  next[idx] = { kind: 'tool', call: { ...prev.call, ...call } }
                  return next
                }
                return [...blocks, { kind: 'tool', call }]
              })
            } else if (eventName === 'chunk') {
              if (typeof data.text === 'string' && data.text) {
                patch((blocks) => appendText(blocks, data.text))
              }
            } else if (eventName === 'error') {
              setError(String(data.message ?? '生成失败'))
            }
          }
        }
      } catch (e: any) {
        if (e?.name !== 'AbortError') {
          const msg = e?.message ?? '网络异常'
          setError(msg)
          patch((blocks) => appendText(blocks, `\n\n_请求失败：${msg}_`))
        }
      } finally {
        abortRef.current = null
        setStreaming(false)
        setMessages((prev) =>
          prev.map((m) => (m.id === assistant.id ? { ...m, streaming: false } : m)),
        )
      }
    },
    [],
  )

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setError(null)
    setStreaming(false)
  }, [])

  return { messages, streaming, error, send, stop, reset }
}
