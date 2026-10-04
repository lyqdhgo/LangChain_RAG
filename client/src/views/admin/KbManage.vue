<script setup>
/**
 * 知识库管理页（仅管理员可访问）
 *
 * 以卡片形式展示知识库，支持新建、编辑、启用/停用、删除。
 * 每个知识库在 Chroma 中对应一个独立的 collection，删除时会一并清理向量数据。
 */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import * as kbApi from '@/api/kb'
import { COVER_COLORS } from '@/utils/constants'

const router = useRouter()

/* ==================== 列表与查询 ==================== */

const loading = ref(false)
const kbList = ref([])
const total = ref(0)
const categories = ref([])

// 查询条件
const query = reactive({
  page: 1,
  size: 8,
  keyword: '',
  category: '',
})

/**
 * 加载知识库列表
 */
async function loadList() {
  loading.value = true
  try {
    const data = await kbApi.getKbList(query)
    kbList.value = data.list
    total.value = data.total
  } catch {
    kbList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/**
 * 加载分类下拉选项
 */
async function loadCategories() {
  try {
    categories.value = await kbApi.getKbCategories()
  } catch {
    categories.value = []
  }
}

/**
 * 查询
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
  query.category = ''
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

/* ==================== 新增 / 编辑 ==================== */

const dialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)
const formRef = ref(null)

// 表单数据
const form = reactive({
  id: null,
  name: '',
  description: '',
  category: '通用',
  cover_color: COVER_COLORS[0],
  status: 1,
})

// 表单校验规则
const rules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { max: 100, message: '名称不能超过 100 个字符', trigger: 'blur' },
  ],
}

const dialogTitle = ref('新建知识库')

/**
 * 打开新建弹窗
 */
function openCreate() {
  dialogMode.value = 'create'
  dialogTitle.value = '新建知识库'
  Object.assign(form, {
    id: null, name: '', description: '',
    category: '通用', cover_color: COVER_COLORS[0], status: 1,
  })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

/**
 * 打开编辑弹窗
 * @param {object} kb 知识库对象
 */
function openEdit(kb) {
  dialogMode.value = 'edit'
  dialogTitle.value = '编辑知识库'
  Object.assign(form, {
    id: kb.id,
    name: kb.name,
    description: kb.description || '',
    category: kb.category || '通用',
    cover_color: kb.cover_color || COVER_COLORS[0],
    status: kb.status,
  })
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

/**
 * 提交表单
 */
async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await kbApi.createKb({ ...form })
      ElMessage.success('知识库创建成功，接下来可以上传文档了')
    } else {
      await kbApi.updateKb(form.id, { ...form })
      ElMessage.success('修改成功')
    }
    dialogVisible.value = false
    loadList()
    loadCategories()
  } catch {
    // 错误提示已由拦截器处理
  } finally {
    submitting.value = false
  }
}

/* ==================== 行操作 ==================== */

/**
 * 启用 / 停用知识库
 * @param {object} kb 知识库对象
 */
async function handleToggleStatus(kb) {
  const nextStatus = kb.status === 1 ? 0 : 1
  try {
    await kbApi.updateKb(kb.id, { status: nextStatus })
    ElMessage.success(nextStatus === 1 ? '已启用该知识库' : '已停用该知识库')
    loadList()
  } catch {
    // 错误提示已由拦截器处理
  }
}

/**
 * 删除知识库
 * @param {object} kb 知识库对象
 */
async function handleDelete(kb) {
  try {
    await ElMessageBox.confirm(
      `确定要删除知识库「${kb.name}」吗？<br/>该知识库下的 <b>${kb.doc_count || 0}</b> 份文档记录与全部向量数据都会被清除，且无法恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error',
        dangerouslyUseHTMLString: true,
      },
    )
  } catch {
    return
  }

  try {
    await kbApi.deleteKb(kb.id)
    ElMessage.success('知识库已删除')
    if (kbList.value.length === 1 && query.page > 1) {
      query.page -= 1
    }
    loadList()
    loadCategories()
  } catch {
    // 错误提示已由拦截器处理
  }
}

/**
 * 跳转到文档管理页，并自动按该知识库过滤
 * @param {object} kb 知识库对象
 */
function goDocuments(kb) {
  router.push({ path: '/admin/doc', query: { kb_id: kb.id } })
}

onMounted(() => {
  loadList()
  loadCategories()
})
</script>

<template>
  <div class="page-container">
    <!-- ==================== 查询工具条 ==================== -->
    <div class="panel">
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索知识库名称"
          clearable
          style="width: 240px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select v-model="query.category" placeholder="全部分类" clearable style="width: 160px">
          <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
        </el-select>

        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>查询
        </el-button>
        <el-button @click="resetQuery">
          <el-icon><Refresh /></el-icon>重置
        </el-button>

        <div class="toolbar-right">
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon>新建知识库
          </el-button>
        </div>
      </div>
    </div>

    <!-- ==================== 知识库卡片列表 ==================== -->
    <div v-loading="loading" class="kb-list">
      <el-empty
        v-if="!loading && !kbList.length"
        description="还没有知识库，点击右上角「新建知识库」开始吧"
        class="empty-block"
      />

      <el-row v-else :gutter="16">
        <el-col v-for="kb in kbList" :key="kb.id" :xs="24" :sm="12" :lg="6">
          <div class="kb-card" :class="{ 'is-disabled': kb.status === 0 }">
            <!-- 顶部色条，颜色取自知识库的主题色 -->
            <div class="kb-cover" :style="{ backgroundColor: kb.cover_color }">
              <el-icon :size="28"><Collection /></el-icon>
            </div>

            <div class="kb-body">
              <div class="kb-head">
                <h3 class="kb-name" :title="kb.name">{{ kb.name }}</h3>
                <el-tag :type="kb.status === 1 ? 'success' : 'info'" size="small" effect="plain">
                  {{ kb.status === 1 ? '启用' : '停用' }}
                </el-tag>
              </div>

              <el-tag size="small" type="info" effect="plain" class="kb-category">
                {{ kb.category || '通用' }}
              </el-tag>

              <p class="kb-desc" :title="kb.description">
                {{ kb.description || '暂无描述' }}
              </p>

              <div class="kb-stats">
                <div class="kb-stat">
                  <el-icon><Document /></el-icon>
                  <span>{{ kb.doc_count || 0 }} 份文档</span>
                </div>
                <div class="kb-time">{{ kb.create_time }}</div>
              </div>

              <div class="kb-actions">
                <el-button link type="primary" size="small" @click="goDocuments(kb)">
                  查看文档
                </el-button>
                <el-button link type="primary" size="small" @click="openEdit(kb)">编辑</el-button>
                <el-button
                  link
                  :type="kb.status === 1 ? 'warning' : 'success'"
                  size="small"
                  @click="handleToggleStatus(kb)"
                >
                  {{ kb.status === 1 ? '停用' : '启用' }}
                </el-button>
                <el-button link type="danger" size="small" @click="handleDelete(kb)">删除</el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- ==================== 分页 ==================== -->
    <div v-if="total > query.size" class="pagination-wrap">
      <el-pagination
        :current-page="query.page"
        :page-size="query.size"
        :total="total"
        layout="total, prev, pager, next"
        background
        @current-change="handlePageChange"
      />
    </div>

    <!-- ==================== 新建 / 编辑弹窗 ==================== -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="知识库名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：人事管理制度" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="所属分类" prop="category">
          <el-input v-model="form.category" placeholder="例如：人事制度 / 技术文档" />
        </el-form-item>

        <el-form-item label="知识库描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="简单描述这个知识库包含哪些内容，方便其他同事理解"
          />
        </el-form-item>

        <el-form-item label="主题颜色" prop="cover_color">
          <div class="color-picker">
            <span
              v-for="color in COVER_COLORS"
              :key="color"
              class="color-item"
              :class="{ active: form.cover_color === color }"
              :style="{ backgroundColor: color }"
              @click="form.cover_color = color"
            >
              <el-icon v-if="form.cover_color === color"><Check /></el-icon>
            </span>
          </div>
        </el-form-item>

        <el-form-item v-if="dialogMode === 'edit'" label="状态" prop="status">
          <el-switch
            v-model="form.status"
            :active-value="1"
            :inactive-value="0"
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ dialogMode === 'create' ? '确定创建' : '保存修改' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ---------- 卡片列表 ---------- */
.kb-list {
  min-height: 200px;
}

.empty-block {
  background-color: var(--app-card-bg);
  border-radius: 8px;
  padding: 40px 0;
}

.kb-card {
  display: flex;
  flex-direction: column;
  background-color: var(--app-card-bg);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
  height: calc(100% - 16px);
  transition: box-shadow 0.2s, transform 0.2s;
}

.kb-card:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

/* 停用的知识库整体降低存在感，避免被误用 */
.kb-card.is-disabled {
  opacity: 0.6;
}

.kb-cover {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 72px;
  color: #fff;
}

.kb-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 14px 16px 10px;
}

.kb-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.kb-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--app-text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-category {
  align-self: flex-start;
  margin: 8px 0;
}

.kb-desc {
  flex: 1;
  font-size: 13px;
  line-height: 1.6;
  color: var(--app-text-secondary);
  margin: 0 0 12px;
  /* 描述最多显示两行，超出省略 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--app-text-muted);
  padding-bottom: 10px;
  border-bottom: 1px solid #f2f3f5;
}

.kb-stat {
  display: flex;
  align-items: center;
  gap: 4px;
}

.kb-actions {
  display: flex;
  align-items: center;
  padding-top: 6px;
}

/* ---------- 主题色选择 ---------- */
.color-picker {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.color-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  color: #fff;
  border: 2px solid transparent;
  transition: transform 0.15s;
}

.color-item:hover {
  transform: scale(1.1);
}

.color-item.active {
  border-color: var(--app-text-primary);
}
</style>
