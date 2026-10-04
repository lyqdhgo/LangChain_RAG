<script setup>
/**
 * 个人中心
 *
 * 左侧展示账号信息与系统状态，右侧提供「修改资料」与「修改密码」两个表单。
 */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import * as authApi from '@/api/auth'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()

// 当前激活的标签页
const activeTab = ref('profile')

/* ==================== 个人资料 ==================== */

const profileFormRef = ref(null)
const profileSubmitting = ref(false)

// 资料表单，初始值取当前登录用户信息
const profileForm = reactive({
  nickname: userStore.userInfo?.nickname || '',
  email: userStore.userInfo?.email || '',
  phone: userStore.userInfo?.phone || '',
})

// 资料表单校验规则
const profileRules = {
  nickname: [
    { required: true, message: '请输入用户昵称', trigger: 'blur' },
    { max: 50, message: '昵称不能超过 50 个字符', trigger: 'blur' },
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }],
}

/**
 * 提交个人资料修改
 */
async function handleUpdateProfile() {
  const valid = await profileFormRef.value.validate().catch(() => false)
  if (!valid) return

  profileSubmitting.value = true
  try {
    const data = await authApi.updateProfile({ ...profileForm })
    // 同步更新全局状态与 localStorage，顶部导航的名字会立即变化
    userStore.updateLocalUser(data)
    ElMessage.success('资料修改成功')
  } catch {
    // 错误提示已由拦截器处理
  } finally {
    profileSubmitting.value = false
  }
}

/* ==================== 修改密码 ==================== */

const passwordFormRef = ref(null)
const passwordSubmitting = ref(false)

// 密码表单
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

/**
 * 确认密码的自定义校验：必须与新密码一致
 */
function validateConfirmPassword(rule, value, callback) {
  if (!value) {
    callback(new Error('请再次输入新密码'))
  } else if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

// 密码表单校验规则
const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度需在 6 到 32 位之间', trigger: 'blur' },
  ],
  confirm_password: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
}

/**
 * 提交修改密码
 */
async function handleUpdatePassword() {
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return

  passwordSubmitting.value = true
  try {
    await authApi.updatePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码修改成功，请使用新密码重新登录')

    // 密码已变更，退出登录让用户用新密码登录
    setTimeout(async () => {
      await userStore.logout()
      router.push('/login')
    }, 1200)
  } catch {
    // 错误提示已由拦截器处理
  } finally {
    passwordSubmitting.value = false
  }
}

/* ==================== 系统状态 ==================== */

const systemStatus = ref(null)
const statusLoading = ref(false)

/**
 * 加载系统运行状态（Ollama 与模型情况）
 */
async function loadSystemStatus() {
  statusLoading.value = true
  try {
    systemStatus.value = await authApi.getSystemStatus()
  } catch {
    systemStatus.value = null
  } finally {
    statusLoading.value = false
  }
}

// 系统整体是否可用
function isSystemReady() {
  return systemStatus.value?.ollama_online && !systemStatus.value?.missing_models?.length
}

// 当前用户展示的角色名
function roleText() {
  return userStore.userInfo?.role === 'admin' ? '管理员' : '普通用户'
}

onMounted(loadSystemStatus)
</script>

<template>
  <div class="profile-page">
    <div class="profile-container">
      <el-row :gutter="16">
        <!-- ==================== 左侧：账号信息 ==================== -->
        <el-col :xs="24" :lg="8">
          <div class="panel user-card">
            <el-avatar :size="72" class="user-avatar">
              {{ userStore.displayName.charAt(0) }}
            </el-avatar>
            <h2 class="user-name">{{ userStore.displayName }}</h2>
            <div class="user-role">
              <el-tag :type="userStore.isAdmin ? 'danger' : 'primary'" effect="plain" size="small">
                {{ roleText() }}
              </el-tag>
            </div>

            <el-divider />

            <div class="info-list">
              <div class="info-item">
                <span class="info-label">登录账号</span>
                <span class="info-value">{{ userStore.userInfo?.username }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">所属部门</span>
                <span class="info-value">{{ userStore.userInfo?.department || '未设置' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">邮箱</span>
                <span class="info-value">{{ userStore.userInfo?.email || '未设置' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">手机号</span>
                <span class="info-value">{{ userStore.userInfo?.phone || '未设置' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">最近登录</span>
                <span class="info-value">{{ userStore.userInfo?.last_login_time || '-' }}</span>
              </div>
            </div>
          </div>

          <!-- 系统运行状态 -->
          <div v-loading="statusLoading" class="panel status-panel">
            <h3 class="panel-title">系统状态</h3>

            <template v-if="systemStatus">
              <div class="status-item">
                <span class="status-label">Ollama 服务</span>
                <span class="status-value" :class="systemStatus.ollama_online ? 'ok' : 'bad'">
                  <span class="dot"></span>
                  {{ systemStatus.ollama_online ? '运行中' : '未连接' }}
                </span>
              </div>
              <div class="status-item">
                <span class="status-label">对话模型</span>
                <span class="status-value">{{ systemStatus.llm_model }}</span>
              </div>
              <div class="status-item">
                <span class="status-label">嵌入模型</span>
                <span class="status-value">{{ systemStatus.embedding_model }}</span>
              </div>

              <el-alert
                v-if="!isSystemReady()"
                type="warning"
                :closable="false"
                show-icon
                class="status-alert"
              >
                <template #title>
                  <span v-if="!systemStatus.ollama_online">
                    Ollama 服务未启动，请先执行 <code>ollama serve</code>
                  </span>
                  <span v-else>
                    缺少模型：{{ systemStatus.missing_models.join('、') }}，请执行
                    <code>ollama pull {{ systemStatus.missing_models[0] }}</code>
                  </span>
                </template>
              </el-alert>
            </template>

            <el-empty v-else description="无法获取系统状态" :image-size="60" />
          </div>
        </el-col>

        <!-- ==================== 右侧：表单区 ==================== -->
        <el-col :xs="24" :lg="16">
          <div class="panel">
            <el-tabs v-model="activeTab">
              <!-- 修改资料 -->
              <el-tab-pane label="修改资料" name="profile">
                <el-form
                  ref="profileFormRef"
                  :model="profileForm"
                  :rules="profileRules"
                  label-width="90px"
                  class="form-box"
                >
                  <el-form-item label="登录账号">
                    <!-- 账号由管理员分配，这里只读展示 -->
                    <el-input :model-value="userStore.userInfo?.username" disabled />
                  </el-form-item>

                  <el-form-item label="用户昵称" prop="nickname">
                    <el-input v-model="profileForm.nickname" placeholder="请输入用户昵称" />
                  </el-form-item>

                  <el-form-item label="邮箱" prop="email">
                    <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
                  </el-form-item>

                  <el-form-item label="手机号" prop="phone">
                    <el-input v-model="profileForm.phone" placeholder="请输入手机号" />
                  </el-form-item>

                  <el-form-item>
                    <el-button
                      type="primary"
                      :loading="profileSubmitting"
                      @click="handleUpdateProfile"
                    >
                      保存修改
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-tab-pane>

              <!-- 修改密码 -->
              <el-tab-pane label="修改密码" name="password">
                <el-form
                  ref="passwordFormRef"
                  :model="passwordForm"
                  :rules="passwordRules"
                  label-width="90px"
                  class="form-box"
                >
                  <el-form-item label="原密码" prop="old_password">
                    <el-input
                      v-model="passwordForm.old_password"
                      type="password"
                      show-password
                      placeholder="请输入当前使用的密码"
                    />
                  </el-form-item>

                  <el-form-item label="新密码" prop="new_password">
                    <el-input
                      v-model="passwordForm.new_password"
                      type="password"
                      show-password
                      placeholder="请输入新密码（6 - 32 位）"
                    />
                  </el-form-item>

                  <el-form-item label="确认密码" prop="confirm_password">
                    <el-input
                      v-model="passwordForm.confirm_password"
                      type="password"
                      show-password
                      placeholder="请再次输入新密码"
                    />
                  </el-form-item>

                  <el-form-item>
                    <el-button
                      type="primary"
                      :loading="passwordSubmitting"
                      @click="handleUpdatePassword"
                    >
                      确认修改
                    </el-button>
                    <span class="form-tip">修改成功后需要重新登录</span>
                  </el-form-item>
                </el-form>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  height: 100%;
  overflow-y: auto;
  padding: 16px;
}

.profile-container {
  max-width: 1200px;
  margin: 0 auto;
}

/* ---------- 左侧用户卡片 ---------- */
.user-card {
  text-align: center;
  margin-bottom: 16px;
}

.user-avatar {
  background-color: #409eff;
  color: #fff;
  font-size: 28px;
  margin-bottom: 12px;
}

.user-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--app-text-primary);
  margin: 0 0 8px;
}

.user-role {
  margin-bottom: 4px;
}

.info-list {
  text-align: left;
}

.info-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 0;
  font-size: 13px;
  border-bottom: 1px solid #f2f3f5;
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  color: var(--app-text-muted);
  flex-shrink: 0;
}

.info-value {
  color: var(--app-text-primary);
  text-align: right;
  word-break: break-all;
}

/* ---------- 系统状态 ---------- */
.status-panel {
  margin-bottom: 16px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 0;
  font-size: 13px;
  border-bottom: 1px solid #f2f3f5;
}

.status-item:last-of-type {
  border-bottom: none;
}

.status-label {
  color: var(--app-text-muted);
  flex-shrink: 0;
}

.status-value {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--app-text-primary);
  text-align: right;
  word-break: break-all;
}

.status-value .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-value.ok {
  color: #0ca30c;
}

.status-value.ok .dot {
  background-color: #0ca30c;
}

.status-value.bad {
  color: #d03b3b;
}

.status-value.bad .dot {
  background-color: #d03b3b;
}

.status-alert {
  margin-top: 12px;
}

.status-alert code {
  background-color: rgba(0, 0, 0, 0.06);
  border-radius: 3px;
  padding: 1px 5px;
  font-family: Consolas, Monaco, monospace;
}

/* ---------- 表单区 ---------- */
.form-box {
  max-width: 460px;
  padding-top: 8px;
}

.form-tip {
  font-size: 12px;
  color: var(--app-text-muted);
  margin-left: 12px;
}
</style>
