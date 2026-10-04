<script setup>
/**
 * 问答记录页（仅管理员可访问）
 *
 * 以「提问」为维度展示所有用户的问答明细，展开行可以看到 AI 的完整回答与引用来源。
 * 支持按提问内容、提问人、知识库筛选。
 */
import { onMounted, reactive, ref } from 'vue'

import * as chatApi from '@/api/chat'
import * as kbApi from '@/api/kb'
import * as userApi from '@/api/user'
import { formatDuration, formatScore, scoreTagType } from '@/utils/format'

/* ==================== 列表与查询 ==================== */

const loading = ref(false)
const tableData = ref([])
const total = ref(0)

// 筛选项的下拉数据
const userOptions = ref([])
const kbOptions = ref([])

// 查询条件
const query = reactive({
  page: 1,
  size: 10,
  keyword: '',
  user_id: null,
  kb_id: null,
})

/**
 * 加载问答记录
 */
async function loadList() {
  loading.value = true
  try {
    const data = await chatApi.getChatRecords(query)
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
 * 加载筛选下拉选项
 */
async function loadOptions() {
  try {
    // 两个请求互相独立，并发执行
    const [users, kbs] = await Promise.all([
      userApi.getUserOptions(),
      kbApi.getKbList({ all: 1 }),
    ])
    userOptions.value = users
    kbOptions.value = kbs
  } catch {
    userOptions.value = []
    kbOptions.value = []
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
  query.user_id = null
  query.kb_id = null
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

onMounted(() => {
  loadList()
  loadOptions()
})
</script>

<template>
  <div class="page-container">
    <div class="panel">
      <!-- ==================== 查询工具条 ==================== -->
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索提问内容"
          clearable
          style="width: 240px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select v-model="query.user_id" placeholder="全部提问人" clearable filterable style="width: 160px">
          <el-option
            v-for="user in userOptions"
            :key="user.id"
            :label="`${user.nickname}（${user.username}）`"
            :value="user.id"
          />
        </el-select>

        <el-select v-model="query.kb_id" placeholder="全部知识库" clearable style="width: 180px">
          <el-option v-for="kb in kbOptions" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>

        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>查询
        </el-button>
        <el-button @click="resetQuery">
          <el-icon><Refresh /></el-icon>重置
        </el-button>
      </div>

      <!-- ==================== 记录表格 ==================== -->
      <el-table
        v-loading="loading"
        :data="tableData"
        border
        stripe
        style="width: 100%"
        row-key="id"
      >
        <!-- 展开行：展示 AI 完整回答与引用来源 -->
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-box">
              <div class="expand-section">
                <div class="expand-label">
                  <el-icon><MagicStick /></el-icon>AI 回答
                </div>
                <div class="expand-answer">{{ row.answer || '（该问题没有对应的回答记录）' }}</div>
              </div>

              <div v-if="row.sources && row.sources.length" class="expand-section">
                <div class="expand-label">
                  <el-icon><Document /></el-icon>引用来源（共 {{ row.sources.length }} 个片段）
                </div>
                <div class="source-list">
                  <div v-for="(source, index) in row.sources" :key="index" class="source-item">
                    <div class="source-head">
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
              </div>

              <el-empty
                v-else
                description="这条回答没有引用知识库内容"
                :image-size="60"
                class="expand-empty"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="id" label="ID" width="70" align="center" />

        <el-table-column label="提问人" width="130">
          <template #default="{ row }">
            <span class="username-text">{{ row.username }}</span>
          </template>
        </el-table-column>

        <el-table-column label="提问内容" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="question-text">{{ row.question }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="kb_name" label="知识库" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.kb_name }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="引用" width="90" align="center">
          <template #default="{ row }">
            <span class="chunk-text">{{ row.sources?.length || 0 }} 个</span>
          </template>
        </el-table-column>

        <el-table-column label="回答耗时" width="110" align="center">
          <template #default="{ row }">
            <span class="chunk-text">{{ formatDuration(row.response_time) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="create_time" label="提问时间" width="170" align="center" />
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
  </div>
</template>

<style scoped>
.username-text {
  font-size: 14px;
  color: var(--app-text-primary);
}

.question-text {
  color: var(--app-text-primary);
}

.chunk-text {
  font-size: 13px;
  color: var(--app-text-primary);
  font-variant-numeric: tabular-nums;
}

/* ---------- 展开行 ---------- */
.expand-box {
  padding: 16px 24px 16px 48px;
  background-color: #fafbfc;
}

.expand-section {
  margin-bottom: 16px;
}

.expand-section:last-child {
  margin-bottom: 0;
}

.expand-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-secondary);
  margin-bottom: 8px;
}

.expand-answer {
  font-size: 14px;
  line-height: 1.8;
  color: var(--app-text-primary);
  background-color: #fff;
  border-radius: 6px;
  padding: 12px 16px;
  border: 1px solid var(--app-border);
  /* 保留模型输出中的换行 */
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---------- 引用来源 ---------- */
.source-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-item {
  background-color: #fff;
  border: 1px solid var(--app-border);
  border-radius: 6px;
  padding: 10px 14px;
}

.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.source-icon {
  color: #2a78d6;
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
  /* 来源片段最多显示三行 */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.expand-empty {
  padding: 8px 0;
}
</style>
