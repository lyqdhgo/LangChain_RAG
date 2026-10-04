/**
 * 通用格式化工具方法
 */

/**
 * 格式化文件大小
 * @param {number} size 字节数
 * @returns {string} 例如 "1.25 MB"
 */
export function formatFileSize(size) {
  const bytes = Number(size) || 0
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

/**
 * 格式化耗时（毫秒 → 秒）
 * @param {number} ms 毫秒
 * @returns {string} 例如 "3.2 秒"
 */
export function formatDuration(ms) {
  if (!ms) return '-'
  return `${(ms / 1000).toFixed(1)} 秒`
}

/**
 * 把相似度得分转成百分比展示
 *
 * 后端返回的 score 是余弦相似度，范围大致在 0~1 之间；
 * 分数过低时说明召回质量一般，这里统一按百分比显示，并在前端做颜色区分。
 *
 * @param {number} score 相似度
 * @returns {string} 例如 "92%"
 */
export function formatScore(score) {
  if (score === null || score === undefined) return '-'
  return `${Math.round(Number(score) * 100)}%`
}

/**
 * 获取相似度对应的标签颜色
 * @param {number} score 相似度
 * @returns {string} Element Plus 的标签类型
 */
export function scoreTagType(score) {
  const value = Number(score) || 0
  if (value >= 0.8) return 'success'
  if (value >= 0.6) return 'warning'
  return 'info'
}
