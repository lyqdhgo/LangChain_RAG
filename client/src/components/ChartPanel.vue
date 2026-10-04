<script setup>
/**
 * 图表卡片组件
 *
 * 统一的「标题 + 右上角操作区 + 图表内容」结构，避免每个图表重复写卡片样式。
 */
defineProps({
  // 卡片标题
  title: {
    type: String,
    required: true,
  },
  // 标题下方的补充说明
  subtitle: {
    type: String,
    default: '',
  },
  // 图表区域高度
  height: {
    type: String,
    default: '300px',
  },
  // 是否正在加载（显示骨架屏）
  loading: {
    type: Boolean,
    default: false,
  },
  // 无数据时的提示文案
  emptyText: {
    type: String,
    default: '暂无数据',
  },
  // 数据是否为空
  empty: {
    type: Boolean,
    default: false,
  },
})
</script>

<template>
  <div class="chart-panel">
    <div class="panel-header">
      <div class="panel-title-group">
        <h3 class="panel-title">{{ title }}</h3>
        <span v-if="subtitle" class="panel-subtitle">{{ subtitle }}</span>
      </div>
      <!-- 右上角操作区，例如时间范围切换 -->
      <div class="panel-extra">
        <slot name="extra" />
      </div>
    </div>

    <div v-loading="loading" class="panel-body" :style="{ height }">
      <!--
        图表容器始终保持渲染：ECharts 实例绑定的 DOM 一旦被销毁，
        重新有数据时就无法再绘制，所以空状态用覆盖层展示而不是替换掉图表。
      -->
      <slot />

      <div v-if="empty && !loading" class="empty-mask">
        <el-empty :description="emptyText" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-panel {
  background-color: var(--app-card-bg);
  border-radius: 8px;
  padding: 16px 16px 12px;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--app-text-primary);
  margin: 0;
}

.panel-subtitle {
  font-size: 12px;
  color: var(--app-text-muted);
}

.panel-extra {
  flex-shrink: 0;
}

.panel-body {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 图表容器需要撑满卡片 */
.panel-body > :deep(div) {
  width: 100%;
  height: 100%;
}

/* 空状态覆盖层：盖在图表上方，不破坏图表 DOM */
.empty-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--app-card-bg);
}
</style>
