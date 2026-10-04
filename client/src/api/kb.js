/**
 * 知识库与文档接口
 *
 * 对应后端 routes/kb_routes.py
 */
import request from './request'

/* ==================== 一、知识库 ==================== */

/**
 * 分页查询知识库列表
 * @param {{page?: number, size?: number, keyword?: string, category?: string, all?: number}} params
 *        all=1 时不分页，返回全部启用的知识库（用于下拉选择）
 */
export function getKbList(params) {
  return request.get('/kb/list', { params })
}

/**
 * 查询知识库详情
 * @param {number} id 知识库ID
 */
export function getKbDetail(id) {
  return request.get(`/kb/detail/${id}`)
}

/**
 * 获取所有知识库分类（筛选用）
 */
export function getKbCategories() {
  return request.get('/kb/categories')
}

/**
 * 新建知识库
 * @param {{name: string, description?: string, category?: string, cover_color?: string}} data
 */
export function createKb(data) {
  return request.post('/kb/create', data)
}

/**
 * 修改知识库
 * @param {number} id 知识库ID
 * @param {object} data 待修改字段
 */
export function updateKb(id, data) {
  return request.put(`/kb/update/${id}`, data)
}

/**
 * 删除知识库（逻辑删除，同时会清空其向量数据）
 * @param {number} id 知识库ID
 */
export function deleteKb(id) {
  return request.delete(`/kb/delete/${id}`)
}

/* ==================== 二、文档 ==================== */

/**
 * 分页查询文档列表
 * @param {{page?: number, size?: number, kb_id?: number, keyword?: string, status?: number}} params
 */
export function getDocList(params) {
  return request.get('/kb/doc/list', { params })
}

/**
 * 上传文档（后端会自动触发解析与向量化）
 * @param {number} kbId 目标知识库ID
 * @param {File} file 文件对象
 * @param {(percent: number) => void} onProgress 上传进度回调
 */
export function uploadDoc(kbId, file, onProgress) {
  const formData = new FormData()
  formData.append('kb_id', kbId)
  formData.append('file', file)

  return request.post('/kb/doc/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded * 100) / event.total))
      }
    },
  })
}

/**
 * 重新向量化文档（向量化失败或更换嵌入模型后使用）
 * @param {number} id 文档ID
 */
export function reindexDoc(id) {
  return request.post(`/kb/doc/reindex/${id}`)
}

/**
 * 删除文档（同时删除物理文件与向量数据）
 * @param {number} id 文档ID
 */
export function deleteDoc(id) {
  return request.delete(`/kb/doc/delete/${id}`)
}
