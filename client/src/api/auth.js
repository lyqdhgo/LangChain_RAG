/**
 * 认证相关接口
 *
 * 对应后端 routes/auth_routes.py
 */
import request from './request'

/**
 * 用户登录
 * @param {{username: string, password: string}} data 账号密码
 * @returns {Promise<{token: string, user: object}>}
 */
export function login(data) {
  return request.post('/auth/login', data)
}

/**
 * 获取当前登录用户信息（刷新页面后用它恢复登录状态）
 */
export function getUserInfo() {
  return request.get('/auth/info')
}

/**
 * 退出登录
 */
export function logout() {
  return request.post('/auth/logout')
}

/**
 * 修改当前用户密码
 * @param {{old_password: string, new_password: string}} data
 */
export function updatePassword(data) {
  return request.put('/auth/password', data)
}

/**
 * 修改当前用户个人资料
 * @param {{nickname?: string, email?: string, phone?: string}} data
 */
export function updateProfile(data) {
  return request.put('/auth/profile', data)
}

/**
 * 获取系统运行状态（Ollama 是否在线、模型是否就绪）
 */
export function getSystemStatus() {
  return request.get('/auth/system/status')
}
