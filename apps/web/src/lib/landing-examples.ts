/**
 * 空状态引导。
 *
 * 每条都写成「一句能直接发出去的话」—— 用户点一下就能看到完整流程，
 * 不用自己组织语言。这比罗列功能介绍有效得多。
 */

export interface LandingExample {
  id: string
  /** 分类标签 */
  label: string
  /** 卡片标题 */
  title: string
  /** 实际发送的内容 */
  prompt: string
}

export const LANDING_EXAMPLES: LandingExample[] = [
  {
    id: 'niche',
    label: '选品',
    title: '这个品类能不能做',
    prompt:
      '我想做厨房小家电，预算 5 万，主要走拼多多和淘宝。帮我采集这个类目的价格分布和竞品情况，跑一遍五维选品分析，告诉我能不能进场。',
  },
  {
    id: 'compare',
    label: '比价',
    title: '同款在三家平台的差价',
    prompt:
      '帮我对比一下「便携榨汁杯」在 1688、淘宝、拼多多三个平台的价格和销量，找出利润空间最大的货源组合。',
  },
  {
    id: 'creative',
    label: '出图',
    title: '给新品做一套主图',
    prompt:
      '这是一款硅胶折叠水杯，主打通勤和户外，目标人群是 25-35 岁女性。帮我策划一套主图方案，包含白底图、场景图和卖点图。',
  },
  {
    id: 'ops',
    label: '运营',
    title: '这批货该怎么清',
    prompt:
      '我有一批库存积压了 90 天，占用资金大概 3 万。帮我判断该降价清货还是继续等等，给出具体的价格策略。',
  },
]
