/**
 * 输入类「托盘」表面的共用规格。
 *
 * 首页的提问框和对话页的输入框是**同一个东西的两种状态**，
 * 所以阴影、圆角、高度上限必须同源 —— 各自写一份的话，
 * 改了一处另一处就会悄悄走样。
 *
 * 规格学自 OpenAlice 的公开设计文档：外壳用大圆角 + 多层极淡阴影当边界，
 * **不描边**。描边会让它看起来像个表单，阴影才像个「可以往里放东西的托盘」。
 */

export const SHELL_RADIUS = 26
export const MIN_HEIGHT = 68
export const MAX_HEIGHT = 168

/** 常态：四层，从发丝般的轮廓到远处的大范围柔光。 */
export const SHELL_SHADOW =
  '0 0 0 1px color-mix(in srgb, var(--foreground) 4%, transparent), ' +
  '0 2px 8px color-mix(in srgb, var(--foreground) 4%, transparent), ' +
  '0 14px 52px color-mix(in srgb, var(--foreground) 8%, transparent), ' +
  'inset 0 1px 0 color-mix(in srgb, var(--foreground) 4%, transparent)'

/** 聚焦：同一组阴影整体略微加深。比换颜色克制，也比加描边准确。 */
export const SHELL_SHADOW_FOCUS =
  '0 0 0 1px color-mix(in srgb, var(--foreground) 5%, transparent), ' +
  '0 2px 8px color-mix(in srgb, var(--foreground) 5%, transparent), ' +
  '0 14px 52px color-mix(in srgb, var(--foreground) 10%, transparent), ' +
  'inset 0 1px 0 color-mix(in srgb, var(--foreground) 6%, transparent)'

/** 正文阅读宽度。736px 是长文本一行不累的常见上限。 */
export const READING_MEASURE = 736

/** 对话区与输入框共用同一套左右内边距，保证两者左边缘严格对齐。 */
export const MEASURE_PADDING = `px-[max(24px,calc((100%-${READING_MEASURE}px)/2))]`
