<script setup>
/**
 * 智能问答页（管理员与普通用户共用）
 *
 * 页面结构：
 *   左侧：会话列表（新建、重命名、删除）+ 知识库范围选择
 *   右侧：消息区（用户提问 / AI 回答 / 引用来源）+ 输入框
 *
 * 回答采用 SSE 流式输出，边生成边显示，形成打字机效果。
 */
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import * as chatApi from '@/api/chat'
import * as kbApi from '@/api/kb'
import MarkdownView from '@/components/MarkdownView.vue'
import { formatDuration, formatScore, scoreTagType } from '@/utils/format'

/* ==================== 状态定义 ==================== */

const loadingSessions = ref(false)
const loadingMessages = ref(false)
const sending = ref(false)          // 是否正在等待回答
const streaming = ref(false)        // 是否正在流式输出

// 会话列表
const sessions = ref([])

// 当前会话
const currentSession = ref(null)

// 当前会话的消息列表
const messages = ref([])

// 知识库下拉选项（用于新建会话时选择检索范围）
const kbOptions = ref([])

// 新建会话时选择的知识库ID，0 表示全部知识库
const selectedKbId = ref(0)

// 输入框内容
const inputText = ref('')

// 消息区与输入框的 DOM 引用，用于自动滚动
const messageAreaRef = ref(null)
const inputRef = ref(null)

// 用于中途停止生成
let abortController = null

// 输入框最大字数，与后端校验保持一致
const MAX_QUESTION_LENGTH = 500

/* ==================== 计算属性 ==================== */

// 当前会话标题
const currentTitle = computed(() => currentSession.value?.title || '新的对话')

// 当前会话使用的知识库名称
const currentKbName = computed(() => {
  if (!currentSession.value?.kb_id) return '全部知识库'
  return currentSession.value.kb_name || '全部知识库'
})

// 输入框剩余可输入字数
const remainingLength = computed(() => MAX_QUESTION_LENGTH - inputText.value.length)

// 是否可以发送
const canSend = computed(() =>
  inputText.value.trim().length > 0 && !sending.value && remainingLength.value >= 0,
)

// 没有消息时展示欢迎引导
const showWelcome = computed(() => !messages.value.length && !loadingMessages.value)

// 推荐问题（空状态时展示，点击可直接提问）
const suggestions = [
  '公司的年假有多少天？怎么申请？',
  '差旅费报销的标准是什么？需要哪些材料？',
  '新员工入职第一天需要办理哪些手续？',
  '代码提交和 Git 分支管理有哪些规范？',
]

/* ==================== 会话管理 ==================== */

/**
 * 加载会话列表
 */
async function loadSessions() {
  loadingSessions.value = true
  try {
    const data = await chatApi.getSessionList({ page: 1, size: 50 })
    sessions.value = data.list
  } catch {
    sessions.value = []
  } finally {
    loadingSessions.value = false
  }
}

/**
 * 加载知识库下拉选项
 */
async function loadKbOptions() {
  try {
    kbOptions.value = await kbApi.getKbList({ all: 1 })
  } catch {
    kbOptions.value = []
  }
}

/**
 * 新建会话
 * @returns {Promise<object|null>} 新建的会话对象
 */
async function createSession() {
  try {
    const session = await chatApi.createSession({
      // 0 表示在全部知识库中检索，后端会把它转成 null
      kb_id: selectedKbId.value,
      title: '新的对话',
    })
    // 新会话插入到列表最前面
    sessions.value.unshift(session)
    currentSession.value = session
    messages.value = []
    return session
  } catch {
    return null
  }
}

/**
 * 切换到指定会话
 * @param {object} session 会话对象
 */
async function selectSession(session) {
  // 正在生成回答时不允许切换，避免消息串到别的会话里
  if (sending.value) {
    ElMessage.warning('当前回答还在生成中，请稍候再切换会话')
    return
  }

  currentSession.value = session
  loadingMessages.value = true
  messages.value = []
  try {
    const data = await chatApi.getSessionMessages(session.id)
    messages.value = data.messages
    scrollToBottom()
  } catch {
    messages.value = []
  } finally {
    loadingMessages.value = false
  }
}

/**
 * 重命名会话
 * @param {object} session 会话对象
 */
async function handleRename(session) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的会话名称', '重命名会话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: session.title,
      inputValidator: (text) => (text && text.trim() ? true : '名称不能为空'),
    })
    await chatApi.renameSession(session.id, value.trim())
    session.title = value.trim()
    ElMessage.success('重命名成功')
  } catch {
    // 用户取消或接口失败（失败时拦截器已提示）
  }
}

/**
 * 删除会话
 * @param {object} session 会话对象
 */
async function handleDeleteSession(session) {
  try {
    await ElMessageBox.confirm(
      `确定要删除会话「${session.title}」吗？删除后聊天记录将无法恢复。`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' },
    )
  } catch {
    return
  }

  try {
    await chatApi.deleteSession(session.id)
    ElMessage.success('会话已删除')

    // 从列表中移除
    sessions.value = sessions.value.filter((item) => item.id !== session.id)

    // 如果删除的正是当前会话，清空右侧内容
    if (currentSession.value?.id === session.id) {
      currentSession.value = null
      messages.value = []
    }
  } catch {
    // 错误提示已由拦截器处理
  }
}

/* ==================== 消息发送 ==================== */

/**
 * 滚动消息区到底部
 */
function scrollToBottom() {
  nextTick(() => {
    const el = messageAreaRef.value
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  })
}

/**
 * 发送提问（流式输出）
 * @param {string} presetQuestion 预设问题（点击推荐问题时使用）
 */
async function handleSend(presetQuestion) {
  const question = (presetQuestion ?? inputText.value).trim()

  if (!question) {
    ElMessage.warning('请输入你的问题')
    return
  }
  if (question.length > MAX_QUESTION_LENGTH) {
    ElMessage.warning(`问题太长了，请控制在 ${MAX_QUESTION_LENGTH} 字以内`)
    return
  }
  if (sending.value) return

  // 还没有会话时，先自动创建一个
  if (!currentSession.value) {
    const session = await createSession()
    if (!session) return
  }

  // 清空输入框
  inputText.value = ''

  // 1. 先把用户提问显示出来
  messages.value.push({
    id: `local-user-${Date.now()}`,
    role: 'user',
    content: question,
    sources: [],
    response_time: 0,
    create_time: formatNow(),
  })

  // 2. 插入一条空的 AI 消息，用于接收流式返回的内容
  const aiMessage = {
    id: `local-ai-${Date.now()}`,
    role: 'assistant',
    content: '',
    sources: [],
    response_time: 0,
    create_time: formatNow(),
    streaming: true,   // 标记正在生成，模板中显示光标动画
  }
  messages.value.push(aiMessage)

  sending.value = true
  streaming.value = true
  scrollToBottom()

  // 3. 发起流式请求
  abortController = new AbortController()

  await chatApi.askQuestionStream(
    { session_id: currentSession.value.id, question },
    {
      // 收到引用来源
      onSources(sources) {
        aiMessage.sources = sources || []
      },
      // 收到答案片段：追加到消息内容后面，形成打字机效果
      onMessage(chunk) {
        aiMessage.content += chunk
        scrollToBottom()
      },
      // 回答完成
      onDone(info) {
        aiMessage.response_time = info?.elapsed || 0
        aiMessage.streaming = false
        streaming.value = false
        // 后端会用第一个问题作为会话标题，这里同步一下列表显示
        syncSessionTitle(question)
        scrollToBottom()
      },
      // 出错
      onError(message) {
        aiMessage.streaming = false
        if (!aiMessage.content) {
          aiMessage.content = `抱歉，回答生成失败：${message}`
        }
        ElMessage.error(message)
      },
    },
    abortController.signal,
  )

  // 4. 收尾：如果流结束时没有触发 onDone（例如被中断），保证状态被复位
  if (aiMessage.streaming) {
    aiMessage.streaming = false
  }
  sending.value = false
  streaming.value = false
  abortController = null

  // 5. 刷新会话列表，让标题与消息数保持最新
  refreshCurrentSession()
  inputRef.value?.focus()
}

/**
 * 停止生成
 */
function handleStop() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }

  const last = messages.value[messages.value.length - 1]
  if (last && last.streaming) {
    last.streaming = false
    if (!last.content) {
      last.content = '（已停止生成）'
    }
  }

  sending.value = false
  streaming.value = false
  ElMessage.info('已停止生成')
}

/**
 * 同步会话标题：后端首次提问时会用问题前 30 个字作为标题
 * @param {string} question 用户问题
 */
function syncSessionTitle(question) {
  const session = currentSession.value
  if (!session) return
  if (!session.title || session.title === '新的对话') {
    session.title = question.slice(0, 30)
  }
  session.message_count = (session.message_count || 0) + 2
}

/**
 * 从服务端刷新当前会话信息与列表
 */
async function refreshCurrentSession() {
  try {
    const data = await chatApi.getSessionList({ page: 1, size: 50 })
    sessions.value = data.list
    if (currentSession.value) {
      const latest = data.list.find((item) => item.id === currentSession.value.id)
      if (latest) currentSession.value = latest
    }
  } catch {
    // 刷新失败不影响主流程
  }
}

/**
 * 获取当前时间字符串（本地消息占位用）
 * @returns {string} 例如 "2024-05-20 14:30:00"
 */
function formatNow() {
  const now = new Date()
  const pad = (num) => String(num).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} `
    + `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

/**
 * 键盘事件：回车发送，Shift + 回车换行
 * @param {KeyboardEvent} event 键盘事件
 */
function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

onMounted(() => {
  loadSessions()
  loadKbOptions()
})
</script>

<template>
  <div class="chat-page">
    <!-- ==================== 左侧：会话列表 ==================== -->
    <aside class="session-panel">
      <!-- 新建会话区 -->
      <div class="new-session">
        <el-select v-model="selectedKbId" size="default" style="width: 100%" placeholder="选择检索范围">
          <el-option label="全部知识库" :value="0" />
          <el-option v-for="kb in kbOptions" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>

        <el-button type="primary" class="new-btn" :disabled="sending" @click="createSession">
          <el-icon><Plus /></el-icon>新建对话
        </el-button>
      </div>

      <!-- 会话列表 -->
      <div v-loading="loadingSessions" class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSession?.id === session.id }"
          @click="selectSession(session)"
        >
          <el-icon class="session-icon"><ChatLineSquare /></el-icon>
          <div class="session-info">
            <div class="session-title" :title="session.title">{{ session.title }}</div>
            <div class="session-meta">
              <span>{{ session.update_time?.slice(5, 16) }}</span>
              <span>·</span>
              <span>{{ session.message_count }} 条</span>
            </div>
          </div>

          <!-- 操作按钮，鼠标悬停时显示 -->
          <div class="session-actions" @click.stop>
            <el-icon class="action-icon" title="重命名" @click="handleRename(session)">
              <EditPen />
            </el-icon>
            <el-icon class="action-icon danger" title="删除" @click="handleDeleteSession(session)">
              <Delete />
            </el-icon>
          </div>
        </div>

        <el-empty
          v-if="!loadingSessions && !sessions.length"
          description="还没有对话记录"
          :image-size="70"
        />
      </div>
    </aside>

    <!-- ==================== 右侧：消息区 ==================== -->
    <section class="chat-main">
      <!-- 顶部信息栏 -->
      <header class="chat-header">
        <div class="header-title">
          <h2>{{ currentTitle }}</h2>
          <el-tag size="small" effect="plain" type="info">
            <el-icon><Collection /></el-icon>
            {{ currentKbName }}
          </el-tag>
        </div>
        <div v-if="streaming" class="header-status">
          <span class="status-dot"></span>正在生成回答…
        </div>
      </header>

      <!-- 消息列表 -->
      <div ref="messageAreaRef" v-loading="loadingMessages" class="message-area">
        <!-- 欢迎引导 -->
        <div v-if="showWelcome" class="welcome">
          <el-icon class="welcome-icon"><MagicStick /></el-icon>
          <h3>你好，我是企业知识库智能助手</h3>
          <p>我可以根据公司内部的制度文档、技术规范为你解答问题，答案都会标注引用来源。</p>

          <div class="suggestion-list">
            <div
              v-for="(item, index) in suggestions"
              :key="index"
              class="suggestion-item"
              @click="handleSend(item)"
            >
              <el-icon><ChatDotRound /></el-icon>
              <span>{{ item }}</span>
            </div>
          </div>
        </div>

        <!-- 消息气泡 -->
        <div
          v-for="message in messages"
          :key="message.id"
          class="message-row"
          :class="message.role === 'user' ? 'is-user' : 'is-ai'"
        >
          <!-- 头像 -->
          <el-avatar :size="34" class="message-avatar" :class="message.role">
            <el-icon v-if="message.role === 'assistant'"><MagicStick /></el-icon>
            <span v-else>我</span>
          </el-avatar>

          <div class="message-body">
            <div class="message-bubble">
              <!-- 用户提问：纯文本展示 -->
              <template v-if="message.role === 'user'">
                {{ message.content }}
              </template>

              <!-- AI 回答：Markdown 渲染 -->
              <template v-else>
                <MarkdownView :content="message.content" />
                <!-- 生成中的光标动画 -->
                <span v-if="message.streaming" class="typing-cursor"></span>
              </template>
            </div>

            <!-- 引用来源 -->
            <div v-if="message.role === 'assistant' && message.sources?.length" class="sources">
              <el-collapse>
                <el-collapse-item>
                  <template #title>
                    <div class="sources-title">
                      <el-icon><Document /></el-icon>
                      引用来源 {{ message.sources.length }} 个片段
                    </div>
                  </template>

                  <div class="source-list">
                    <div v-for="(source, index) in message.sources" :key="index" class="source-item">
                      <div class="source-head">
                        <span class="source-index">{{ index + 1 }}</span>
                        <el-icon class="source-icon"><Document /></el-icon>
                        <span class="source-name">{{ source.file_name || '未知文档' }}</span>
                        <el-tag size="small" effect="plain" type="info">
                          {{ source.kb_name || '未知知识库' }}
                        </el-tag>
                        <el-tag
                          v-if="source.score !== undefined"
                          size="small"
                          :type="scoreTagType(source.score)"
                          effect="plain"
                        >
                          相似度 {{ formatScore(source.score) }}
                        </el-tag>
                      </div>
                      <div v-if="source.content" class="source-content">{{ source.content }}</div>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>

            <!-- 底部信息：时间与耗时 -->
            <div v-if="message.role === 'assistant' && !message.streaming && message.response_time" class="message-footer">
              用时 {{ formatDuration(message.response_time) }}
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <footer class="input-area">
        <div class="input-box">
          <el-input
            ref="inputRef"
            v-model="inputText"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="请输入你的问题，按 Enter 发送，Shift + Enter 换行"
            :disabled="sending"
            @keydown="handleKeydown"
          />
          <div class="input-actions">
            <span class="input-tip" :class="{ warn: remainingLength < 50 }">
              {{ remainingLength }} 字可用
            </span>

            <el-button v-if="streaming" type="danger" plain @click="handleStop">
              <el-icon><VideoPause /></el-icon>停止生成
            </el-button>
            <el-button v-else type="primary" :disabled="!canSend" @click="handleSend()">
              <el-icon><Promotion /></el-icon>发送
            </el-button>
          </div>
        </div>
        <div class="input-hint">
          回答由本地部署的大模型基于知识库内容生成，重要信息请以原始文档为准
        </div>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ==================== 左侧会话面板 ==================== */
.session-panel {
  display: flex;
  flex-direction: column;
  width: 280px;
  flex-shrink: 0;
  background-color: #fff;
  border-right: 1px solid var(--app-border);
}

.new-session {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-bottom: 1px solid var(--app-border);
}

.new-btn {
  width: 100%;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background-color 0.2s;
}

.session-item:hover {
  background-color: #f5f7fa;
}

.session-item.active {
  background-color: #ecf5ff;
}

.session-icon {
  font-size: 16px;
  color: var(--app-text-muted);
  flex-shrink: 0;
}

.session-item.active .session-icon {
  color: #409eff;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 14px;
  color: var(--app-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  gap: 4px;
  font-size: 12px;
  color: var(--app-text-muted);
  margin-top: 2px;
}

/* 操作按钮默认隐藏，悬停时才出现，保持列表干净 */
.session-actions {
  display: none;
  gap: 8px;
  flex-shrink: 0;
}

.session-item:hover .session-actions {
  display: flex;
}

.action-icon {
  font-size: 15px;
  color: var(--app-text-muted);
}

.action-icon:hover {
  color: #409eff;
}

.action-icon.danger:hover {
  color: #d03b3b;
}

/* ==================== 右侧主区域 ==================== */
.chat-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background-color: var(--app-page-bg);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 24px;
  background-color: #fff;
  border-bottom: 1px solid var(--app-border);
  flex-shrink: 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.header-title h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--app-text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #2a78d6;
  flex-shrink: 0;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: #2a78d6;
  animation: blink 1.2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}

/* ---------- 消息区 ---------- */
.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* 欢迎引导 */
.welcome {
  max-width: 680px;
  margin: 40px auto;
  text-align: center;
}

.welcome-icon {
  font-size: 48px;
  color: #409eff;
}

.welcome h3 {
  font-size: 18px;
  color: var(--app-text-primary);
  margin: 16px 0 8px;
}

.welcome p {
  font-size: 14px;
  color: var(--app-text-secondary);
  line-height: 1.7;
  margin: 0 0 28px;
}

.suggestion-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background-color: #fff;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  font-size: 13px;
  color: var(--app-text-secondary);
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-item:hover {
  border-color: #409eff;
  color: #409eff;
  box-shadow: 0 2px 10px rgba(64, 158, 255, 0.12);
}

/* 消息行 */
.message-row {
  display: flex;
  gap: 12px;
  max-width: 900px;
  margin: 0 auto 24px;
}

/* 用户消息靠右显示 */
.message-row.is-user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.message-avatar.assistant {
  background-color: #409eff;
  color: #fff;
}

.message-avatar.user {
  background-color: #67c23a;
  color: #fff;
  font-size: 13px;
}

.message-body {
  min-width: 0;
  max-width: calc(100% - 46px);
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 10px;
  background-color: #fff;
  border: 1px solid var(--app-border);
  font-size: 14px;
  line-height: 1.8;
  color: var(--app-text-primary);
  word-break: break-word;
  white-space: pre-wrap;
}

/* AI 气泡保留 Markdown 的排版，不再强制 pre-wrap */
.message-row.is-ai .message-bubble {
  white-space: normal;
}

.is-user .message-bubble {
  background-color: #409eff;
  border-color: #409eff;
  color: #fff;
}

/* 打字机光标 */
.typing-cursor {
  display: inline-block;
  width: 7px;
  height: 15px;
  margin-left: 2px;
  background-color: #409eff;
  vertical-align: text-bottom;
  animation: blink 0.9s step-end infinite;
}

.message-footer {
  font-size: 12px;
  color: var(--app-text-muted);
  margin-top: 6px;
  padding-left: 4px;
}

/* ---------- 引用来源 ---------- */
.sources {
  margin-top: 8px;
}

.sources :deep(.el-collapse) {
  border: none;
}

.sources :deep(.el-collapse-item__header) {
  height: 34px;
  line-height: 34px;
  border-bottom: none;
  background-color: transparent;
  font-size: 13px;
  color: var(--app-text-secondary);
}

.sources :deep(.el-collapse-item__wrap) {
  border-bottom: none;
  background-color: transparent;
}

.sources :deep(.el-collapse-item__content) {
  padding-bottom: 0;
}

.sources-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.source-item {
  background-color: #fff;
  border: 1px solid var(--app-border);
  border-radius: 6px;
  padding: 10px 12px;
}

.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.source-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background-color: #e8f1fd;
  color: #2a78d6;
  font-size: 11px;
  flex-shrink: 0;
}

.source-icon {
  color: #2a78d6;
  flex-shrink: 0;
}

.source-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--app-text-primary);
}

.source-content {
  font-size: 13px;
  line-height: 1.7;
  color: var(--app-text-secondary);
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--app-border);
  max-height: 120px;
  overflow-y: auto;
}

/* ---------- 输入区 ---------- */
.input-area {
  flex-shrink: 0;
  padding: 12px 24px 16px;
  background-color: #fff;
  border-top: 1px solid var(--app-border);
}

.input-box {
  max-width: 900px;
  margin: 0 auto;
}

.input-box :deep(.el-textarea__inner) {
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.7;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
}

.input-tip {
  font-size: 12px;
  color: var(--app-text-muted);
  font-variant-numeric: tabular-nums;
}

.input-tip.warn {
  color: #ec835a;
}

.input-hint {
  max-width: 900px;
  margin: 8px auto 0;
  font-size: 12px;
  color: var(--app-text-muted);
  text-align: center;
}
</style>
