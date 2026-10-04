<script setup>
/**
 * 用户管理页（仅管理员可访问）
 *
 * 功能：用户列表查询、新增、编辑、启用/禁用、重置密码、删除。
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import * as userApi from '@/api/user'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

/* ==================== 列表与查询 ==================== */

const loading = ref(false)
const tableData = ref([])
const total = ref(0)

// 查询条件
const query = reactive({
  page: 1,
  size: 10,
  keyword: '',
  role: '',
  status: null,
})

/**
 * 加载用户列表
 */
async function loadList() {
  loading.value = true
  try {
    const data = await userApi.getUserList(query)
    tableData.value = data.list
    total.value = data.total
  } catch {
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/**
 * 点击查询：回到第一页重新加载
 */
function handleSearch() {
  query.page = 1
  loadList()
}

/**
 * 重置查询条件
 */
function resetQuery() {
  query.keyword = ''
  query.role = ''
  query.status = null
  query.page = 1
  loadList()
}

/**
 * 切换页码
 * @param {number} page 目标页码
 */
function handlePageChange(page) {
  query.page = page
  loadList()
}

/**
 * 切换每页条数
 * @param {number} size 每页条数
 */
function handleSizeChange(size) {
  query.size = size
  query.page = 1
  loadList()
}

/* ==================== 新增 / 编辑 ==================== */

const dialogVisible = ref(false)
const dialogMode = ref('create')  // create=新增 edit=编辑
const submitting = ref(false)
const formRef = ref(null)

// 表单数据
const form = reactive({
  id: null,
  username: '',
  nickname: '',
  password: '',
  email: '',
  phone: '',
  department: '',
  role: 'user',
})

// 表单校验规则
const rules = {
  username: [
    { required: true, message: '请输入登录账号', trigger: 'blur' },
    { min: 3, max: 50, message: '账号长度需在 3 到 50 个字符之间', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }],
}

// 弹窗标题
const dialogTitle = ref('新增用户')

/**
 * 打开新增用户弹窗
 */
function openCreate() {
  dialogMode.value = 'create'
  dialogTitle.value = '新增用户'
  Object.assign(form, {
    id: null, username: '', nickname: '', password: '',
    email: '', phone: '', department: '', role: 'user',
  })
  dialogVisible.value = true
  // 清除上一次可能残留的校验提示
  formRef.value?.clearValidate()
}

/**
 * 打开编辑用户弹窗
 * @param {object} row 当前行数据
 */
function openEdit(row) {
  dialogMode.value = 'edit'
  dialogTitle.value = '编辑用户'
  Object.assign(form, {
    id: row.id,
    username: row.username,
    nickname: row.nickname || '',
    password: '',
    email: row.email || '',
    phone: row.phone || '',
    department: row.department || '',
    role: row.role,
  })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

/**
 * 提交新增 / 编辑表单
 */
async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      const data = await userApi.createUser({ ...form })
      ElMessage.success('新增成功，初始密码为 123456')
      // 新增后跳到最后一页查看结果
      query.page = 1
    } else {
      await userApi.updateUser(form.id, { ...form })
      ElMessage.success('修改成功')
    }
    dialogVisible.value = false
    loadList()
  } catch {
    // 错误提示已由拦截器处理
  } finally {
    submitting.value = false
  }
}

/* ==================== 行操作 ==================== */

/**
 * 启用 / 禁用用户
 * @param {object} row 当前行数据
 */
async function handleToggleStatus(row) {
  const nextStatus = row.status === 1 ? 0 : 1
  const actionText = nextStatus === 1 ? '启用' : '禁用'

  try {
    await ElMessageBox.confirm(
      `确定要${actionText}用户「${row.nickname || row.username}」吗？`,
      '提示',
      { confirmButtonText: `确定${actionText}`, cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await userApi.changeUserStatus(row.id, nextStatus)
    ElMessage.success(`已${actionText}该账号`)
    loadList()
  } catch {
    // 错误提示已由拦截器处理
  }
}

/**
 * 重置用户密码为 123456
 * @param {object} row 当前行数据
 */
async function handleResetPassword(row) {
  try {
    await ElMessageBox.confirm(
      `确定要将用户「${row.nickname || row.username}」的密码重置为 123456 吗？`,
      '提示',
      { confirmButtonText: '确定重置', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await userApi.resetUserPassword(row.id)
    ElMessage.success('密码已重置为 123456')
  } catch {
    // 错误提示已由拦截器处理
  }
}

/**
 * 删除用户
 * @param {object} row 当前行数据
 */
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${row.nickname || row.username}」吗？删除后该账号将无法登录。`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' },
    )
  } catch {
    return
  }

  try {
    await userApi.deleteUser(row.id)
    ElMessage.success('删除成功')
    // 如果当前页删空了，自动往前翻一页
    if (tableData.value.length === 1 && query.page > 1) {
      query.page -= 1
    }
    loadList()
  } catch {
    // 错误提示已由拦截器处理
  }
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <div class="panel">
      <!-- ==================== 查询工具条 ==================== -->
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索账号 / 昵称 / 手机号"
          clearable
          style="width: 240px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select v-model="query.role" placeholder="全部角色" clearable style="width: 130px">
          <el-option label="管理员" value="admin" />
          <el-option label="普通用户" value="user" />
        </el-select>

        <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 130px">
          <el-option label="正常" :value="1" />
          <el-option label="已禁用" :value="0" />
        </el-select>

        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>查询
        </el-button>
        <el-button @click="resetQuery">
          <el-icon><Refresh /></el-icon>重置
        </el-button>

        <div class="toolbar-right">
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon>新增用户
          </el-button>
        </div>
      </div>

      <!-- ==================== 用户表格 ==================== -->
      <el-table
        v-loading="loading"
        :data="tableData"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="70" align="center" />

        <el-table-column label="用户" min-width="160">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="30" class="cell-avatar">
                {{ (row.nickname || row.username).charAt(0) }}
              </el-avatar>
              <div class="user-cell-text">
                <div class="user-nickname">{{ row.nickname || '-' }}</div>
                <div class="user-account">@{{ row.username }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="角色" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" effect="plain" size="small">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="department" label="所属部门" width="120" align="center">
          <template #default="{ row }">{{ row.department || '-' }}</template>
        </el-table-column>

        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.email || '-' }}</template>
        </el-table-column>

        <el-table-column prop="phone" label="手机号" width="130" align="center">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>

        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- 状态用「圆点 + 文字」表达，不只依赖颜色 -->
            <span class="status-cell" :class="row.status === 1 ? 'is-normal' : 'is-disabled'">
              <span class="status-dot"></span>
              {{ row.status === 1 ? '正常' : '已禁用' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="last_login_time" label="最近登录" width="170" align="center">
          <template #default="{ row }">{{ row.last_login_time || '从未登录' }}</template>
        </el-table-column>

        <el-table-column label="操作" width="230" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              link
              :type="row.status === 1 ? 'warning' : 'success'"
              size="small"
              :disabled="row.id === userStore.userInfo?.id"
              @click="handleToggleStatus(row)"
            >
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
            <el-button link type="info" size="small" @click="handleResetPassword(row)">重置密码</el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.id === userStore.userInfo?.id"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- ==================== 分页 ==================== -->
      <div class="pagination-wrap">
        <el-pagination
          :current-page="query.page"
          :page-size="query.size"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- ==================== 新增 / 编辑弹窗 ==================== -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="登录账号" prop="username">
          <el-input v-model="form.username" placeholder="请输入登录账号（至少 3 位）" />
        </el-form-item>

        <el-form-item label="用户昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入用户昵称" />
        </el-form-item>

        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="user">普通用户</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="所属部门" prop="department">
          <el-input v-model="form.department" placeholder="例如：研发中心" />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>

        <!-- 新增时才提示初始密码，编辑时密码走「重置密码」入口 -->
        <el-alert
          v-if="dialogMode === 'create'"
          type="info"
          :closable="false"
          show-icon
          title="新用户初始密码为 123456，密码会以 MD5 加密后存入数据库"
        />
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ dialogMode === 'create' ? '确定新增' : '保存修改' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ---------- 用户单元格 ---------- */
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cell-avatar {
  background-color: #e8f1fd;
  color: #2a78d6;
  font-size: 13px;
  flex-shrink: 0;
}

.user-cell-text {
  min-width: 0;
}

.user-nickname {
  font-size: 14px;
  color: var(--app-text-primary);
}

.user-account {
  font-size: 12px;
  color: var(--app-text-muted);
}

/* ---------- 状态单元格 ---------- */
.status-cell {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.is-normal {
  color: #0ca30c;
}

.is-normal .status-dot {
  background-color: #0ca30c;
}

.is-disabled {
  color: var(--app-text-muted);
}

.is-disabled .status-dot {
  background-color: #c3c2b7;
}
</style>
