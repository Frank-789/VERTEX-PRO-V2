/** 对话领域类型。 */

export type Role = 'user' | 'assistant'

/** 工具调用状态。 */
export type ToolStatus = 'running' | 'ok' | 'failed'

export interface ToolCall {
  id: string
  /** 人类可读的工具名，如「1688 搜索」 */
  label: string
  /** 机器标识，如 alibaba.search */
  name: string
  status: ToolStatus
  /** 数据来源可信度 */
  source?: DataSourceKind
  /** 耗时（毫秒） */
  durationMs?: number
  /** 命中条数 */
  count?: number
  /** 失败原因 */
  error?: string
  /** 折叠后展示的细节（原始参数/结果摘要） */
  detail?: string
}

/** 数据来源可信度 —— 这个标注很重要，避免把估算值当真实数据。 */
export type DataSourceKind = 'realtime' | 'upload' | 'cached' | 'estimated'

export const DATA_SOURCE_LABEL: Record<DataSourceKind, string> = {
  realtime: '实时采集',
  upload: '用户上传',
  cached: '缓存',
  estimated: '模型估算',
}

/** 消息里的一个块。一条助手消息可以依次包含多个块。 */
export type Block =
  | { kind: 'text'; text: string }
  | { kind: 'sticker'; file: string; label?: string }
  | { kind: 'tool'; call: ToolCall }

export interface Message {
  id: string
  role: Role
  blocks: Block[]
  createdAt: number
  /** 仍在流式输出中 */
  streaming?: boolean
}

/** 纯文本拼接，供复制用。表情包以 [表情] 占位。 */
export function messageToPlainText(m: Message): string {
  return m.blocks
    .map((b) => {
      if (b.kind === 'text') return b.text
      if (b.kind === 'sticker') return `[表情:${b.label ?? b.file}]`
      return ''
    })
    .join('')
    .trim()
}
