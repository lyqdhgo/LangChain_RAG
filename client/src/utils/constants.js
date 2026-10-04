/**
 * 全局常量
 *
 * 把散落在各处的魔法值集中到这里，修改时只需要改一处。
 */

// 登录令牌在 localStorage 中的键名
export const TOKEN_KEY = 'qa_token'

// 用户信息在 localStorage 中的键名
export const USER_KEY = 'user_info'

// 角色常量
export const ROLE_ADMIN = 'admin'
export const ROLE_USER = 'user'

// 文档处理状态：值与后端 KbDocument 模型保持一致
export const DOC_STATUS = {
  PENDING: 0,     // 待处理
  PROCESSING: 1,  // 向量化中
  SUCCESS: 2,     // 已完成
  FAILED: 3,      // 失败
}

/**
 * 文档状态对应的展示文案与标签颜色
 * 颜色取的是 Element Plus 标签类型，同时对应一套「状态色」：
 * 灰=待处理、黄=处理中、绿=已完成、红=失败
 */
export const DOC_STATUS_MAP = {
  0: { label: '待处理', type: 'info' },
  1: { label: '向量化中', type: 'warning' },
  2: { label: '已完成', type: 'success' },
  3: { label: '失败', type: 'danger' },
}

// 知识库卡片可选主题色
export const COVER_COLORS = [
  '#409EFF', '#67C23A', '#E6A23C', '#F56C6C',
  '#909399', '#9254DE', '#13C2C2',
]
