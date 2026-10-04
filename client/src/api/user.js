/**
 * 用户管理接口（仅管理员可用）
 *
 * 对应后端 routes/user_routes.py
 */
import request from './request'

/**
 * 分页查询用户列表
 * @param {{page?: number, size?: number, keyword?: string, role?: string, status?: number}} params
 * @returns {Promise<{list: Array, total: number, page: number, size: number}>}
 */
export function getUserList(params) {
  return request.get('/user/list', { params })
}

/**
 * 新增用户（初始密码为 123456）
 * @param {object} data 用户信息
 */
export function createUser(data) {
  return request.post('/user/create', data)
}

/**
 * 修改用户信息
 * @param {number} id 用户ID
 * @param {object} data 待修改的字段
 */
export function updateUser(id, data) {
  return request.put(`/user/update/${id}`, data)
}

/**
 * 启用 / 禁用用户
 * @param {number} id 用户ID
 * @param {number} status 1=启用 0=禁用
 */
export function changeUserStatus(id, status) {
  return request.put(`/user/status/${id}`, { status })
}

/**
 * 重置用户密码为 123456
 * @param {number} id 用户ID
 */
export function resetUserPassword(id) {
  return request.put(`/user/reset-password/${id}`)
}

/**
 * 删除用户
 * @param {number} id 用户ID
 */
export function deleteUser(id) {
  return request.delete(`/user/delete/${id}`)
}

/**
 * 获取用户下拉选项（问答记录页筛选用）
 */
export function getUserOptions() {
  return request.get('/user/options')
}
