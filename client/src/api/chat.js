/**
 * 智能问答接口
 *
 * 对应后端 routes/chat_routes.py
 */
import request from './request'
import { TOKEN_KEY } from '@/utils/constants'

/* ==================== 一、会话管理 ==================== */

/**
 * 查询会话列表
 * @param {{page?: number, size?: number, keyword?: string, user_id?: number}} params
 */
export function getSessionList(params) {
  return request.get('/chat/session/list', { params })
}

/**
 * 新建会话
 * @param {{kb_id?: number, title?: string}} data kb_id 传 0 或不传表示在全部知识库中检索
 */
export function createSession(data) {
  return request.post('/chat/session/create', data)
}

/**
 * 重命名会话
 * @param {number} id 会话ID
 * @param {string} title 新标题
 */
export function renameSession(id, title) {
  return request.put(`/chat/session/rename/${id}`, { title })
}

/**
 * 删除会话
 * @param {number} id 会话ID
 */
export function deleteSession(id) {
  return request.delete(`/chat/session/delete/${id}`)
}

/**
 * 查询会话下的全部消息（用于还原聊天记录）
 * @param {number} id 会话ID
 * @returns {Promise<{session: object, messages: Array}>}
 */
export function getSessionMessages(id) {
  return request.get(`/chat/session/messages/${id}`)
}

/* ==================== 二、问答 ==================== */

/**
 * 普通问答（一次性返回完整答案）
 * @param {{session_id: number, question: string}} data
 */
export function askQuestion(data) {
  return request.post('/chat/ask', data)
}

/**
 * 流式问答（SSE，实现打字机效果）
 *
 * 由于浏览器原生的 EventSource 不支持自定义请求头（无法携带 Token）
 * 也不支持 POST，所以这里用 fetch + ReadableStream 手动解析 SSE 数据流。
 *
 * @param {{session_id: number, question: string}} data 请求参数
 * @param {object} handlers 事件回调
 *        onSources(sources)  检索到的引用来源
 *        onMessage(chunk)    本次收到的答案片段
 *        onDone(info)        回答结束，info 含耗时与完整答案
 *        onError(msg)        出错
 * @param {AbortSignal} signal 用于中途取消请求
 */
export async function askQuestionStream(data, handlers = {}, signal) {
  const { onSources, onMessage, onDone, onError } = handlers

  try {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || '/api'}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 手动带上 Token，后端 login_required 装饰器会校验
        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) || ''}`,
      },
      body: JSON.stringify(data),
      signal,
    })

    if (!response.ok) {
      throw new Error(`请求失败，HTTP 状态码 ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''   // 缓冲区：解决一个 SSE 消息被拆成多个网络包的问题

    // 逐块读取响应流
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE 以两个换行作为一条消息的分隔符
      const parts = buffer.split('\n\n')
      // 最后一段可能不完整，留在缓冲区等待下一个数据包
      buffer = parts.pop() || ''

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue

        const payload = line.slice(5).trim()
        // 后端在流结束时发送的终止标记
        if (payload === '[DONE]') return

        try {
          const event = JSON.parse(payload)
          if (event.type === 'sources' && onSources) {
            onSources(event.data)
          } else if (event.type === 'message' && onMessage) {
            onMessage(event.data)
          } else if (event.type === 'done' && onDone) {
            onDone(event.data)
          } else if (event.type === 'error' && onError) {
            onError(event.data)
          }
        } catch {
          // 忽略无法解析的脏数据，不影响整体流程
        }
      }
    }
  } catch (error) {
    // 用户主动取消，不算错误
    if (error.name === 'AbortError') return
    if (onError) onError(error.message || '网络异常')
  }
}

/* ==================== 三、管理端问答记录 ==================== */

/**
 * 问答记录查询（管理员）
 * @param {{page?: number, size?: number, keyword?: string, user_id?: number, kb_id?: number}} params
 */
export function getChatRecords(params) {
  return request.get('/chat/records', { params })
}
