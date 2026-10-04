/**
 * 数据统计接口（管理员首页）
 *
 * 对应后端 routes/stats_routes.py
 */
import request from './request'

/**
 * 顶部统计卡片数据
 * @returns {Promise<{user_count, kb_count, doc_count, chunk_count,
 *                    question_count, today_question_count,
 *                    session_count, active_user_count}>}
 */
export function getOverview() {
  return request.get('/stats/overview')
}

/**
 * 最近 N 天的问答量趋势（折线图）
 * @param {number} days 统计天数，可选 7 / 15 / 30
 * @returns {Promise<{dates: string[], questions: number[], sessions: number[]}>}
 */
export function getTrend(days = 7) {
  return request.get('/stats/trend', { params: { days } })
}

/**
 * 各知识库文档数量排行（柱状图）
 * @returns {Promise<{names: string[], doc_counts: number[], chunk_counts: number[]}>}
 */
export function getKbRank() {
  return request.get('/stats/kb-rank')
}

/**
 * 提问最多的用户排行（横向柱状图）
 * @returns {Promise<{names: string[], counts: number[]}>}
 */
export function getUserRank() {
  return request.get('/stats/user-rank')
}

/**
 * 知识库分类占比（饼图）
 * @returns {Promise<Array<{name: string, value: number}>>}
 */
export function getCategoryStats() {
  return request.get('/stats/category')
}

/**
 * 文档处理状态分布（环形图）
 * @returns {Promise<Array<{name: string, value: number}>>}
 */
export function getDocStatusStats() {
  return request.get('/stats/doc-status')
}

/**
 * 最新提问列表（首页表格）
 * @param {number} limit 取多少条
 */
export function getRecentQuestions(limit = 8) {
  return request.get('/stats/recent-questions', { params: { limit } })
}
