/**
 * axios 请求封装
 *
 * 后端所有接口都返回统一结构：{ code, message, data }
 *   code = 200 表示成功，其它值表示业务失败。
 *
 * 这里做了三件事：
 *   1. 请求拦截：自动在请求头带上登录 Token
 *   2. 响应拦截：把 { code, message, data } 拆开，业务代码直接拿到 data
 *   3. 异常处理：Token 失效时自动跳回登录页
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

import router from '@/router'
import { TOKEN_KEY } from '@/utils/constants'

// 创建 axios 实例
const request = axios.create({
  // 开发环境走 vite 代理（见 vite.config.js），生产环境可通过 .env 指定完整地址
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120000, // 大模型回答较慢，超时时间给宽一些（120 秒）
})

/* ------------------------------------------------------------------
 * 请求拦截器：统一携带 Token
 * ------------------------------------------------------------------ */
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

/* ------------------------------------------------------------------
 * 响应拦截器：拆包 + 错误提示
 * ------------------------------------------------------------------ */
request.interceptors.response.use(
  (response) => {
    const res = response.data

    // 后端返回的不是标准结构（例如文件流），直接原样返回
    if (res == null || typeof res.code === 'undefined') {
      return res
    }

    // 业务成功：直接返回 data，调用方无需再写 .data.data
    if (res.code === 200) {
      return res.data
    }

    // 未登录 / 登录过期：清除本地信息并跳转登录页
    if (res.code === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('user_info')
      ElMessage.error(res.message || '登录已过期，请重新登录')
      router.push('/login')
      return Promise.reject(new Error(res.message))
    }

    // 其它业务错误：弹出提示
    ElMessage.error(res.message || '操作失败')
    return Promise.reject(new Error(res.message))
  },
  (error) => {
    // 网络层面的异常（后端没启动、超时等）
    const message = error.code === 'ECONNABORTED'
      ? '请求超时，大模型可能正在处理，请稍后重试'
      : '网络异常，请确认后端服务已启动'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default request
