<script setup>
/**
 * 登录页
 *
 * 左侧为系统介绍，右侧为登录表单。
 * 登录成功后根据角色跳转到不同首页：管理员 → 数据总览，普通用户 → 智能问答。
 */
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getSystemStatus } from '@/api/auth'
import { useUserStore } from '@/store/user'
import { ROLE_ADMIN } from '@/utils/constants'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

// 登录表单数据
const form = reactive({
  username: '',
  password: '',
})

// 系统运行状态（Ollama 是否就绪）
const systemStatus = ref(null)

// 表单校验规则
const rules = {
  username: [{ required: true, message: '请输入登录账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入登录密码', trigger: 'blur' }],
}

// 演示账号，点击可直接填充表单，方便测试
const demoAccounts = [
  { label: '超级管理员', username: 'admin', role: 'admin' },
  { label: '知识库管理员', username: 'manager', role: 'admin' },
  { label: '普通用户', username: 'zhangsan', role: 'user' },
]

onMounted(() => {
  // 提前探测一次后端与 Ollama 状态，方便排查环境问题
  getSystemStatus()
    .then((data) => { systemStatus.value = data })
    .catch(() => { systemStatus.value = null })
})

/**
 * 点击演示账号，自动填充表单
 * @param {object} account 账号信息
 */
function fillAccount(account) {
  form.username = account.username
  form.password = '123456'
}

/**
 * 提交登录
 */
async function handleLogin() {
  // 先做表单校验
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const user = await userStore.login({ ...form })
    ElMessage.success(`欢迎回来，${user.nickname || user.username}`)

    // 优先跳回被拦截前想访问的页面，否则按角色跳默认首页
    const redirect = route.query.redirect
    if (redirect) {
      router.push(redirect)
    } else {
      router.push(user.role === ROLE_ADMIN ? '/admin/home' : '/chat')
    }
  } catch {
    // 错误提示已由 axios 拦截器统一处理，这里无需重复提示
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <!-- ==================== 左侧介绍区 ==================== -->
      <div class="intro">
        <div class="intro-content">
          <el-icon class="intro-logo"><Reading /></el-icon>
          <h1 class="intro-title">企业知识库问答系统</h1>
          <p class="intro-desc">
            基于 LangChain + RAG 检索增强生成技术，<br />
            把公司制度、技术文档、产品手册变成<br />
            一个能随时对话的智能助手。
          </p>

          <ul class="feature-list">
            <li><el-icon><Check /></el-icon>向量检索，答案有据可依</li>
            <li><el-icon><Check /></el-icon>流式输出，回答实时呈现</li>
            <li><el-icon><Check /></el-icon>本地部署，数据不出内网</li>
          </ul>

          <!-- 系统状态提示：Ollama 未就绪时给出明确指引 -->
          <div v-if="systemStatus" class="status-box">
            <template v-if="systemStatus.ollama_online && !systemStatus.missing_models.length">
              <el-icon class="status-ok"><CircleCheck /></el-icon>
              <span>AI 模型已就绪（{{ systemStatus.llm_model }}）</span>
            </template>
            <template v-else>
              <el-icon class="status-warn"><Warning /></el-icon>
              <span>
                {{
                  systemStatus.ollama_online
                    ? `缺少模型：${systemStatus.missing_models.join('、')}`
                    : 'Ollama 服务未启动，问答功能将不可用'
                }}
              </span>
            </template>
          </div>
        </div>
      </div>

      <!-- ==================== 右侧表单区 ==================== -->
      <div class="form-area">
        <h2 class="form-title">账号登录</h2>
        <p class="form-subtitle">请输入您的账号和密码</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          size="large"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="请输入登录账号" clearable>
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入登录密码"
              show-password
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              class="login-btn"
              :loading="loading"
              @click="handleLogin"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 演示账号快捷填充 -->
        <div class="demo-box">
          <div class="demo-title">演示账号（密码均为 123456）</div>
          <div class="demo-list">
            <el-tag
              v-for="item in demoAccounts"
              :key="item.username"
              :type="item.role === 'admin' ? 'primary' : 'info'"
              effect="plain"
              class="demo-tag"
              @click="fillAccount(item)"
            >
              {{ item.label }}：{{ item.username }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
}

.login-card {
  display: flex;
  width: 900px;
  min-height: 540px;
  background-color: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}

/* ---------- 左侧介绍区 ---------- */
.intro {
  width: 420px;
  background: linear-gradient(160deg, #3a7bd5 0%, #2b5876 100%);
  color: #fff;
  padding: 48px 40px;
  display: flex;
  align-items: center;
}

.intro-logo {
  font-size: 42px;
  margin-bottom: 16px;
}

.intro-title {
  font-size: 24px;
  margin: 0 0 16px;
  font-weight: 600;
}

.intro-desc {
  font-size: 14px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.85);
  margin: 0 0 28px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0 0 28px;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 12px;
}

/* ---------- 状态提示 ---------- */
.status-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
  padding: 10px 12px;
  border-radius: 6px;
  background-color: rgba(255, 255, 255, 0.12);
}

.status-ok {
  color: #7ee787;
  flex-shrink: 0;
  margin-top: 2px;
}

.status-warn {
  color: #ffd666;
  flex-shrink: 0;
  margin-top: 2px;
}

/* ---------- 右侧表单区 ---------- */
.form-area {
  flex: 1;
  padding: 56px 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.form-title {
  font-size: 22px;
  margin: 0 0 8px;
  color: var(--app-text-primary);
}

.form-subtitle {
  font-size: 14px;
  color: var(--app-text-muted);
  margin: 0 0 32px;
}

.login-btn {
  width: 100%;
  letter-spacing: 4px;
}

/* ---------- 演示账号 ---------- */
.demo-box {
  margin-top: 8px;
  padding-top: 20px;
  border-top: 1px dashed var(--app-border);
}

.demo-title {
  font-size: 13px;
  color: var(--app-text-muted);
  margin-bottom: 10px;
}

.demo-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.demo-tag {
  cursor: pointer;
}
</style>
