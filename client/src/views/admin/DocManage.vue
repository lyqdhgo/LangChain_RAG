<script setup>
/**
 * 文档管理页（仅管理员可访问）
 *
 * 功能：文档列表查询、上传（自动向量化）、重新向量化、删除。
 *
 * 关于「向量化」：上传后后端会在后台线程中完成
 * 「解析 → 切分 → 调用嵌入模型计算向量 → 写入 Chroma」的完整流程，
 * 文件较大时耗时较长，所以页面会在有文档处于处理中状态时自动轮询刷新。
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import * as kbApi from '@/api/kb'
import { DOC_STATUS, DOC_STATUS_MAP } from '@/utils/constants'

const route = useRoute()

/* ==================== 列表与查询 ==================== */

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const kbOptions = ref([])

// 查询条件：支持从知识库管理页带 kb_id 跳转过来
const query = reactive({
  page: 1,
  size: 10,
  kb_id: route.query.kb_id ? Number(route.query.kb_id) : null,
  keyword: '',
  status: null,
})

// 轮询定时器：有文档在处理中时才会启动
let pollTimer = null

/**
 * 加载文档列表
 * @param {boolean} silent 静默刷新（不显示加载动画，用于轮询）
 */
async function loadList(silent = false) {
  if (!silent) loading.value = true
  try {
    const data = await kbApi.getDocList(query)
    tableData.value = data.list
    total.value = data.total
    // 根据最新数据决定是否需要继续轮询
    syncPolling()
  } catch {
    if (!silent) {
      tableData.value = []
      total.value = 0
    }
  } finally {
    if (!silent) loading.value = false
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
 * 是否还有文档正在处理（待处理或向量化中）
 */
const hasProcessing = computed(() =>
  tableData.value.some(
    (doc) => doc.status === DOC_STATUS.PENDING || doc.status === DOC_STATUS.PROCESSING,
  ),
)

/**
 * 根据是否有文档在处理，启动或停止轮询
 */
function syncPolling() {
  if (hasProcessing.value) {
    if (!pollTimer) {
      // 每 4 秒静默刷新一次列表，让用户看到向量化进度
      pollTimer = setInterval(() => loadList(true), 4000)
    }
  } else if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
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
 * 重置查询条件（保留从其它页面带过来的知识库筛选）
 */
function resetQuery() {
  query.keyword = ''
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

/* ==================== 上传文档 ==================== */

const uploadVisible = ref(false)
const uploading = ref(false)
const uploadPercent = ref(0)
const uploadFormRef = ref(null)
const selectedFile = ref(null)

// 上传表单
const uploadForm = reactive({
  kb_id: null,
})

// 上传表单校验规则
const uploadRules = {
  kb_id: [{ required: true, message: '请选择目标知识库', trigger: 'change' }],
}

// 允许上传的文件类型，与后端 ALLOWED_EXTENSIONS 保持一致
const ACCEPT_TYPES = '.pdf,.docx,.doc,.txt,.md,.csv'

/**
 * 打开上传弹窗
 */
function openUpload() {
  Object.assign(uploadForm, { kb_id: query.kb_id || null })
  selectedFile.value = null
  uploadPercent.value = 0
  uploadVisible.value = true
  uploadFormRef.value?.clearValidate()
}

/**
 * 选择文件后的回调（限制只能选一个文件）
 * @param {object} file el-upload 包装后的文件对象
 */
function handleFileChange(file) {
  selectedFile.value = file.raw
}

/**
 * 移除已选择的文件
 */
function handleFileRemove() {
  selectedFile.value = null
}

/**
 * 提交上传
 */
async function handleUpload() {
  const valid = await uploadFormRef.value.validate().catch(() => false)
  if (!valid) return

  if (!selectedFile.value) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }

  uploading.value = true
  uploadPercent.value = 0
  try {
    await kbApi.uploadDoc(uploadForm.kb_id, selectedFile.value, (percent) => {
      uploadPercent.value = percent
    })
    ElMessage.success('上传成功，正在后台进行向量化处理')
    uploadVisible.value = false
    query.page = 1
    loadList()
    loadKbOptions()
  } catch {
    // 错误提示已由拦截器处理
  } finally {
    uploading.value = false
  }
}

/* ==================== 行操作 ==================== */

/**
 * 重新向量化
 * @param {object} row 文档数据
 */
async function handleReindex(row) {
  try {
    await ElMessageBox.confirm(
      `确定要重新向量化文档「${row.file_name}」吗？原有向量数据会被覆盖。`,
      '提示',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await kbApi.reindexDoc(row.id)
    ElMessage.success('已开始重新向量化')
    loadList()
  } catch {
    // 错误提示已由拦截器处理
  }
}

/**
 * 删除文档
 * @param {object} row 文档数据
 */
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档「${row.file_name}」吗？该文档的向量数据也会一并清除。`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' },
    )
  } catch {
    return
  }

  try {
    await kbApi.deleteDoc(row.id)
    ElMessage.success('文档已删除')
    if (tableData.value.length === 1 && query.page > 1) {
      query.page -= 1
    }
    loadList()
    loadKbOptions()
  } catch {
    // 错误提示已由拦截器处理
  }
}

/**
 * 获取状态标签配置
 * @param {number} status 状态值
 */
function statusInfo(status) {
  return DOC_STATUS_MAP[status] || { label: '未知', type: 'info' }
}

onMounted(() => {
  loadList()
  loadKbOptions()
})

onBeforeUnmount(() => {
  // 离开页面时务必清除定时器，否则会造成内存泄漏和无意义的请求
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="page-container">
    <div class="panel">
      <!-- ==================== 查询工具条 ==================== -->
      <div class="toolbar">
        <el-select
          v-model="query.kb_id"
          placeholder="全部知识库"
          clearable
          style="width: 200px"
          @change="handleSearch"
        >
          <el-option v-for="kb in kbOptions" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>

        <el-input
          v-model="query.keyword"
          placeholder="搜索文件名"
          clearable
          style="width: 220px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 140px">
          <el-option
            v-for="(item, key) in DOC_STATUS_MAP"
            :key="key"
            :label="item.label"
            :value="Number(key)"
          />
        </el-select>

        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>查询
        </el-button>
        <el-button @click="resetQuery">
          <el-icon><Refresh /></el-icon>重置
        </el-button>

        <div class="toolbar-right">
          <el-button type="primary" @click="openUpload">
            <el-icon><Upload /></el-icon>上传文档
          </el-button>
        </div>
      </div>

      <!-- 有文档正在处理时的提示条 -->
      <el-alert
        v-if="hasProcessing"
        type="info"
        :closable="false"
        show-icon
        class="processing-alert"
      >
        <template #title>
          正在后台进行向量化处理，页面会自动刷新进度。文档越大耗时越长，请耐心等待…
        </template>
      </el-alert>

      <!-- ==================== 文档表格 ==================== -->
      <el-table v-loading="loading" :data="tableData" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />

        <el-table-column label="文件名" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="file-cell">
              <el-icon class="file-icon"><Document /></el-icon>
              <span>{{ row.file_name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="kb_name" label="所属知识库" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.kb_name || '-' }}</template>
        </el-table-column>

        <el-table-column prop="file_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" type="info">
              {{ (row.file_type || '').toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="file_size_text" label="大小" width="100" align="center" />

        <el-table-column label="向量化" width="130" align="center">
          <template #default="{ row }">
            <span v-if="row.status === DOC_STATUS.SUCCESS" class="chunk-text">
              {{ row.chunk_count }} 个片段
            </span>
            <span v-else class="chunk-text muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="130" align="center">
          <template #default="{ row }">
            <!-- 状态用标签 + 文字表达，不只靠颜色区分 -->
            <el-tooltip
              :disabled="row.status !== DOC_STATUS.FAILED || !row.error_msg"
              :content="row.error_msg || ''"
              placement="top"
            >
              <el-tag :type="statusInfo(row.status).type" size="small" effect="light">
                {{ statusInfo(row.status).label }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column prop="uploader_name" label="上传人" width="110" align="center">
          <template #default="{ row }">{{ row.uploader_name || '-' }}</template>
        </el-table-column>

        <el-table-column prop="create_time" label="上传时间" width="170" align="center" />

        <el-table-column label="操作" width="170" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              :disabled="row.status === DOC_STATUS.PROCESSING || row.status === DOC_STATUS.PENDING"
              @click="handleReindex(row)"
            >
              重新向量化
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
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

    <!-- ==================== 上传弹窗 ==================== -->
    <el-dialog v-model="uploadVisible" title="上传文档" width="560px" destroy-on-close>
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="100px">
        <el-form-item label="目标知识库" prop="kb_id">
          <el-select v-model="uploadForm.kb_id" placeholder="请选择文档要归入的知识库" style="width: 100%">
            <el-option
              v-for="kb in kbOptions"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="选择文件">
          <el-upload
            class="uploader"
            drag
            :auto-upload="false"
            :limit="1"
            :accept="ACCEPT_TYPES"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">将文件拖到此处，或<em>点击选择文件</em></div>
            <template #tip>
              <div class="upload-tip">
                支持 PDF、Word、TXT、Markdown、CSV 格式，单个文件不超过 50MB，一次只能上传一个文件
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 上传进度条 -->
        <el-form-item v-if="uploading" label="上传进度">
          <el-progress :percentage="uploadPercent" :stroke-width="10" style="width: 100%" />
        </el-form-item>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="上传完成后，系统会在后台自动解析文档、切分成文本块并计算向量，处理完成后即可在问答中被检索到。"
        />
      </el-form>

      <template #footer>
        <el-button :disabled="uploading" @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          {{ uploading ? '上传中...' : '开始上传' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.processing-alert {
  margin-bottom: 16px;
}

/* ---------- 文件名单元格 ---------- */
.file-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.file-icon {
  color: #2a78d6;
  flex-shrink: 0;
}

.chunk-text {
  font-size: 13px;
  color: var(--app-text-primary);
  /* 数字列使用等宽数字，纵向对齐更整齐 */
  font-variant-numeric: tabular-nums;
}

.chunk-text.muted {
  color: var(--app-text-muted);
}

/* ---------- 上传组件 ---------- */
.uploader {
  width: 100%;
}

.uploader :deep(.el-upload),
.uploader :deep(.el-upload-dragger) {
  width: 100%;
}

.upload-icon {
  font-size: 42px;
  color: #c0c4cc;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 14px;
  color: var(--app-text-secondary);
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  font-size: 12px;
  color: var(--app-text-muted);
  line-height: 1.6;
  margin-top: 6px;
}
</style>
