/**
 * 用户状态管理（Pinia）
 *
 * 负责保存登录令牌与当前用户信息，并提供登录、登出、恢复登录状态等方法。
 * 用户信息同时写入 localStorage，刷新页面后可以恢复登录状态。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import * as authApi from '@/api/auth'
import { TOKEN_KEY, USER_KEY, ROLE_ADMIN } from '@/utils/constants'

export const useUserStore = defineStore('user', () => {
  /* ---------------- 状态 ---------------- */

  // 登录令牌，初始值从 localStorage 读取，实现刷新不掉线
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')

  // 当前用户信息
  const userInfo = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

  /* ---------------- 计算属性 ---------------- */

  // 是否已登录
  const isLogin = computed(() => !!token.value)

  // 是否是管理员
  const isAdmin = computed(() => userInfo.value?.role === ROLE_ADMIN)

  // 展示用的名字，优先取昵称
  const displayName = computed(() => userInfo.value?.nickname || userInfo.value?.username || '')

  /* ---------------- 方法 ---------------- */

  /**
   * 登录：调用接口拿到 Token 与用户信息并保存
   * @param {{username: string, password: string}} form 登录表单
   */
  async function login(form) {
    const data = await authApi.login(form)
    token.value = data.token
    userInfo.value = data.user
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    return data.user
  }

  /**
   * 拉取最新的用户信息（刷新页面时调用，顺便校验 Token 是否还有效）
   */
  async function fetchUserInfo() {
    const data = await authApi.getUserInfo()
    userInfo.value = data
    localStorage.setItem(USER_KEY, JSON.stringify(data))
    return data
  }

  /**
   * 退出登录：通知后端并清空本地状态
   */
  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // 即使接口失败也要保证本地状态被清干净
    }
    clear()
  }

  /**
   * 清空本地登录状态
   */
  function clear() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  /**
   * 本地更新用户信息（修改个人资料后调用，避免多请求一次接口）
   * @param {object} data 新的用户信息
   */
  function updateLocalUser(data) {
    userInfo.value = { ...userInfo.value, ...data }
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo.value))
  }

  return {
    token, userInfo,
    isLogin, isAdmin, displayName,
    login, fetchUserInfo, logout, clear, updateLocalUser,
  }
})
