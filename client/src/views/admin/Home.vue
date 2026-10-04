<script setup>
/**
 * 管理员首页 —— 数据总览
 *
 * 页面结构：
 *   第一行：4 个统计卡片（用户、知识库、文档、提问量）
 *   第二行：问答量趋势折线图 + 文档处理状态环形图
 *   第三行：知识库文档排行柱状图 + 知识库分类占比饼图
 *   第四行：用户提问排行横向柱状图 + 最新提问列表
 *
 * 图表使用 ECharts，公共配色与坐标轴样式统一放在 utils/chartTheme.js 中。
 */
import { computed, onMounted, ref } from 'vue'

import * as statsApi from '@/api/stats'
import ChartPanel from '@/components/ChartPanel.vue'
import { useChart } from '@/composables/useChart'
import {
  SERIES_COLORS,
  STATUS_COLORS,
  baseOption,
  barSeries,
  categoryAxis,
  lineSeries,
  pieSeries,
  valueAxis,
} from '@/utils/chartTheme'

/* ==================== 基础状态 ==================== */

const loading = ref(true)

// 顶部统计卡片数据
const overview = ref({
  user_count: 0,
  kb_count: 0,
  doc_count: 0,
  chunk_count: 0,
  question_count: 0,
  today_question_count: 0,
  session_count: 0,
  active_user_count: 0,
})

// 趋势图的统计天数（可切换 7 / 15 / 30）
const trendDays = ref(7)

// 最新提问列表
const recentQuestions = ref([])

// 各图表的数据是否为空（用于展示空状态）
const trendEmpty = ref(false)
const kbRankEmpty = ref(false)
const userRankEmpty = ref(false)
const categoryEmpty = ref(false)
const docStatusEmpty = ref(false)

// 知识库排行原始数据，图表提示框里要用到「向量片段数」
const kbRankRaw = ref({ names: [], doc_counts: [], chunk_counts: [] })

// 各图表的 DOM 容器
const trendRef = ref(null)
const docStatusRef = ref(null)
const kbRankRef = ref(null)
const categoryRef = ref(null)
const userRankRef = ref(null)

// 初始化图表实例
const trendChart = useChart(trendRef)
const docStatusChart = useChart(docStatusRef)
const kbRankChart = useChart(kbRankRef)
const categoryChart = useChart(categoryRef)
const userRankChart = useChart(userRankRef)

/* ==================== 统计卡片配置 ==================== */

// 把 4 个统计卡片做成配置数组，模板里循环渲染，避免重复代码
const statCards = computed(() => [
  {
    key: 'user',
    label: '系统用户',
    value: overview.value.user_count,
    suffix: '人',
    icon: 'User',
    color: SERIES_COLORS[0],
    tip: `近 7 天活跃 ${overview.value.active_user_count} 人`,
  },
  {
    key: 'kb',
    label: '知识库',
    value: overview.value.kb_count,
    suffix: '个',
    icon: 'Collection',
    color: SERIES_COLORS[2],
    tip: `累计 ${overview.value.chunk_count} 个向量片段`,
  },
  {
    key: 'doc',
    label: '知识文档',
    value: overview.value.doc_count,
    suffix: '份',
    icon: 'Document',
    color: SERIES_COLORS[3],
    tip: '已完成向量化的文档',
  },
  {
    key: 'question',
    label: '累计提问',
    value: overview.value.question_count,
    suffix: '次',
    icon: 'ChatDotRound',
    color: SERIES_COLORS[1],
    tip: `今日新增 ${overview.value.today_question_count} 次`,
  },
])

/* ==================== 数据加载 ==================== */

/**
 * 加载顶部统计卡片数据
 */
async function loadOverview() {
  try {
    overview.value = await statsApi.getOverview()
  } catch {
    // 错误提示已由 axios 拦截器统一处理
  }
}

/**
 * 加载并渲染问答趋势折线图
 */
async function loadTrend() {
  trendChart.showLoading()
  try {
    const data = await statsApi.getTrend(trendDays.value)
    trendEmpty.value = !data.dates.length

    trendChart.setOption({
      ...baseOption({ showLegend: true }),
      tooltip: {
        ...baseOption({ showLegend: true }).tooltip,
        valueFormatter: (value) => `${value} 次`,
      },
      xAxis: categoryAxis(data.dates),
      yAxis: valueAxis(),
      series: [
        lineSeries('提问量', data.questions, 0),
        lineSeries('会话数', data.sessions, 1),
      ],
    })
  } finally {
    trendChart.hideLoading()
  }
}

/**
 * 加载并渲染文档处理状态环形图
 *
 * 使用「状态色」而不是普通系列色：绿=已完成、黄=处理中、灰=待处理、红=失败。
 * 图例中带有文字名称，状态信息不依赖颜色单独传达。
 */
async function loadDocStatus() {
  docStatusChart.showLoading()
  try {
    const data = await statsApi.getDocStatusStats()
    // 过滤掉数量为 0 的状态，避免环形图出现无意义的空扇区
    const valid = data.filter((item) => item.value > 0)
    docStatusEmpty.value = valid.length === 0

    // 状态名 → 状态色 的映射
    const colorMap = {
      待处理: STATUS_COLORS.pending,
      向量化中: STATUS_COLORS.processing,
      已完成: STATUS_COLORS.success,
      失败: STATUS_COLORS.failed,
    }

    docStatusChart.setOption({
      ...baseOption(),
      // 环形图不需要坐标轴，改用图例说明各状态含义
      legend: {
        bottom: 0,
        left: 'center',
        icon: 'circle',
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 14,
        textStyle: { color: '#5c6470', fontSize: 12 },
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255,255,255,0.98)',
        borderColor: '#e4e7ed',
        borderWidth: 1,
        textStyle: { color: '#1f2329', fontSize: 12 },
        formatter: '{b}：{c} 份（{d}%）',
        extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.12); border-radius: 6px;',
      },
      grid: undefined,
      series: [
        {
          ...pieSeries(valid, valid.map((item) => colorMap[item.name] || STATUS_COLORS.pending), true),
          // 环形图中间的汇总数字
          label: {
            show: true,
            position: 'center',
            formatter: () => `{total|${valid.reduce((sum, item) => sum + item.value, 0)}}\n{label|文档总数}`,
            rich: {
              total: { fontSize: 24, fontWeight: 'bold', color: '#1f2329', lineHeight: 32 },
              label: { fontSize: 12, color: '#8a9099' },
            },
          },
          labelLine: { show: false },
          emphasis: { label: { show: true, scale: false }, scaleSize: 4 },
        },
      ],
    })
  } finally {
    docStatusChart.hideLoading()
  }
}

/**
 * 加载并渲染知识库文档排行柱状图
 *
 * 注意：文档数与向量片段数不在一个量级，放在同一个坐标轴上会让柱子高度差异过大，
 * 所以这里只画「文档数」一个系列，向量片段数放进提示框里展示。
 */
async function loadKbRank() {
  kbRankChart.showLoading()
  try {
    const data = await statsApi.getKbRank()
    kbRankRaw.value = data
    kbRankEmpty.value = !data.names.length

    kbRankChart.setOption({
      ...baseOption(),
      tooltip: {
        ...baseOption().tooltip,
        formatter: (params) => {
          const index = params[0].dataIndex
          const docCount = data.doc_counts[index] ?? 0
          const chunkCount = data.chunk_counts[index] ?? 0
          return `${params[0].name}<br/>文档数：${docCount} 份<br/>向量片段：${chunkCount} 个`
        },
      },
      xAxis: {
        ...categoryAxis(data.names),
        // 知识库名称较长，倾斜展示避免重叠
        axisLabel: { color: '#8a9099', fontSize: 12, interval: 0, rotate: 20 },
      },
      yAxis: valueAxis(),
      series: [barSeries('文档数', data.doc_counts, 0)],
    })
  } finally {
    kbRankChart.hideLoading()
  }
}

/**
 * 加载并渲染知识库分类占比饼图
 *
 * 分类超过 6 个时，把排名靠后的合并成「其他」，
 * 避免饼图扇区过多导致颜色循环复用、无法分辨。
 */
async function loadCategory() {
  categoryChart.showLoading()
  try {
    const data = await statsApi.getCategoryStats()
    categoryEmpty.value = !data.length

    const sorted = [...data].sort((a, b) => b.value - a.value)
    const top = sorted.slice(0, 6)
    const rest = sorted.slice(6)
    const chartData = rest.length
      ? [...top, { name: '其他', value: rest.reduce((sum, item) => sum + item.value, 0) }]
      : top

    categoryChart.setOption({
      ...baseOption(),
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255,255,255,0.98)',
        borderColor: '#e4e7ed',
        borderWidth: 1,
        textStyle: { color: '#1f2329', fontSize: 12 },
        formatter: '{b}：{c} 个（{d}%）',
        extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.12); border-radius: 6px;',
      },
      grid: undefined,
      series: [pieSeries(chartData, SERIES_COLORS, false)],
    })
  } finally {
    categoryChart.hideLoading()
  }
}

/**
 * 加载并渲染用户提问排行横向柱状图
 */
async function loadUserRank() {
  userRankChart.showLoading()
  try {
    const data = await statsApi.getUserRank()
    userRankEmpty.value = !data.names.length

    // 横向柱状图需要把类目轴放在 Y 轴、数值轴放在 X 轴
    // 数组反转一次，让提问最多的用户显示在最上方
    userRankChart.setOption({
      ...baseOption(),
      tooltip: {
        ...baseOption().tooltip,
        formatter: (params) => `${params[0].name}<br/>提问 ${params[0].value} 次`,
      },
      xAxis: valueAxis(),
      yAxis: {
        type: 'category',
        data: [...data.names].reverse(),
        axisLine: { lineStyle: { color: '#c3c2b7' } },
        axisTick: { show: false },
        axisLabel: { color: '#8a9099', fontSize: 12 },
      },
      series: [barSeries('提问次数', [...data.counts].reverse(), 0, true)],
    })
  } finally {
    userRankChart.hideLoading()
  }
}

/**
 * 加载最新提问列表
 */
async function loadRecentQuestions() {
  try {
    recentQuestions.value = await statsApi.getRecentQuestions(8)
  } catch {
    recentQuestions.value = []
  }
}

/**
 * 切换趋势图的时间范围
 * @param {number} days 天数
 */
function changeTrendDays(days) {
  if (trendDays.value === days) return
  trendDays.value = days
  loadTrend()
}

/**
 * 一次性加载页面所有数据
 */
async function loadAll() {
  loading.value = true
  try {
    // 各接口相互独立，用 allSettled 并发请求，其中一个失败不影响其它图表
    await Promise.allSettled([
      loadOverview(),
      loadTrend(),
      loadDocStatus(),
      loadKbRank(),
      loadCategory(),
      loadUserRank(),
      loadRecentQuestions(),
    ])
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="home-page">
    <!-- ==================== 第一行：统计卡片 ==================== -->
    <el-row :gutter="16">
      <el-col v-for="card in statCards" :key="card.key" :xs="24" :sm="12" :lg="6">
        <div class="stat-card">
          <div class="stat-icon" :style="{ backgroundColor: `${card.color}1a`, color: card.color }">
            <el-icon :size="24"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-label">{{ card.label }}</div>
            <div class="stat-value">
              {{ card.value }}
              <span class="stat-suffix">{{ card.suffix }}</span>
            </div>
            <div class="stat-tip">{{ card.tip }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ==================== 第二行：趋势 + 文档状态 ==================== -->
    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="16">
        <ChartPanel title="问答量趋势" subtitle="每天的用户提问次数与会话数" :loading="loading">
          <template #extra>
            <el-radio-group :model-value="trendDays" size="small" @change="changeTrendDays">
              <el-radio-button :value="7">近 7 天</el-radio-button>
              <el-radio-button :value="15">近 15 天</el-radio-button>
              <el-radio-button :value="30">近 30 天</el-radio-button>
            </el-radio-group>
          </template>
          <div ref="trendRef" class="chart-box"></div>
        </ChartPanel>
      </el-col>

      <el-col :xs="24" :lg="8">
        <ChartPanel
          title="文档处理状态"
          subtitle="知识库文档的向量化进度"
          :loading="loading"
          :empty="docStatusEmpty"
          empty-text="还没有上传任何文档"
        >
          <div ref="docStatusRef" class="chart-box"></div>
        </ChartPanel>
      </el-col>
    </el-row>

    <!-- ==================== 第三行：知识库排行 + 分类占比 ==================== -->
    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="12">
        <ChartPanel
          title="知识库文档数量"
          subtitle="鼠标悬停可查看对应的向量片段数"
          :loading="loading"
          :empty="kbRankEmpty"
          empty-text="还没有创建知识库"
        >
          <div ref="kbRankRef" class="chart-box"></div>
        </ChartPanel>
      </el-col>

      <el-col :xs="24" :lg="12">
        <ChartPanel
          title="知识库分类占比"
          subtitle="按知识库分类统计"
          :loading="loading"
          :empty="categoryEmpty"
          empty-text="还没有创建知识库"
        >
          <div ref="categoryRef" class="chart-box"></div>
        </ChartPanel>
      </el-col>
    </el-row>

    <!-- ==================== 第四行：用户排行 + 最新提问 ==================== -->
    <el-row :gutter="16" class="row-gap">
      <el-col :xs="24" :lg="12">
        <ChartPanel
          title="用户提问排行"
          subtitle="提问次数最多的前 6 位用户"
          :loading="loading"
          :empty="userRankEmpty"
          empty-text="还没有用户提问"
        >
          <div ref="userRankRef" class="chart-box"></div>
        </ChartPanel>
      </el-col>

      <el-col :xs="24" :lg="12">
        <ChartPanel title="最新提问" subtitle="最近 8 条用户提问记录" :loading="loading" height="300px">
          <div class="recent-list">
            <el-empty v-if="!recentQuestions.length" description="暂无提问记录" :image-size="70" />
            <div v-for="item in recentQuestions" :key="item.id" class="recent-item">
              <el-avatar :size="28" class="recent-avatar">
                {{ item.username.charAt(0) }}
              </el-avatar>
              <div class="recent-main">
                <div class="recent-question" :title="item.question">{{ item.question }}</div>
                <div class="recent-meta">
                  <span>{{ item.username }}</span>
                  <span>{{ item.create_time }}</span>
                </div>
              </div>
            </div>
          </div>
        </ChartPanel>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
/* ---------- 统计卡片 ---------- */
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background-color: var(--app-card-bg);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  transition: box-shadow 0.2s, transform 0.2s;
}

.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 10px;
  flex-shrink: 0;
}

.stat-body {
  min-width: 0;
}

.stat-label {
  font-size: 13px;
  color: var(--app-text-muted);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 26px;
  font-weight: 600;
  color: var(--app-text-primary);
  line-height: 1.2;
}

.stat-suffix {
  font-size: 13px;
  font-weight: 400;
  color: var(--app-text-muted);
  margin-left: 2px;
}

.stat-tip {
  font-size: 12px;
  color: var(--app-text-muted);
  margin-top: 4px;
}

/* ---------- 行间距 ---------- */
.row-gap {
  margin-bottom: 0;
}

.row-gap .el-col {
  margin-bottom: 16px;
}

/* ---------- 最新提问列表 ---------- */
.recent-list {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding-right: 4px;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 4px;
  border-bottom: 1px solid #f2f3f5;
}

.recent-item:last-child {
  border-bottom: none;
}

.recent-avatar {
  background-color: #e8f1fd;
  color: #2a78d6;
  font-size: 13px;
  flex-shrink: 0;
}

.recent-main {
  min-width: 0;
  flex: 1;
}

.recent-question {
  font-size: 13px;
  color: var(--app-text-primary);
  /* 问题过长时省略，鼠标悬停可看完整内容 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--app-text-muted);
  margin-top: 2px;
}
</style>
