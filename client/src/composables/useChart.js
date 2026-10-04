/**
 * ECharts 图表组合式函数
 *
 * 把「初始化 → 设置数据 → 监听容器尺寸变化 → 组件卸载时销毁」这一套
 * 重复逻辑封装起来，页面里只要关心怎么拼 option 即可。
 *
 * 使用示例：
 *   const chartRef = ref(null)
 *   const { setOption } = useChart(chartRef)
 *   setOption({ ... })   // 数据加载完成后调用
 */
import { onBeforeUnmount, onMounted, shallowRef } from 'vue'
import * as echarts from 'echarts'

/**
 * @param {import('vue').Ref<HTMLElement|null>} containerRef 图表容器的 ref
 * @returns {{ setOption: Function, showLoading: Function, hideLoading: Function, resize: Function }}
 */
export function useChart(containerRef) {
  // 用 shallowRef 保存实例，避免 ECharts 实例被 Vue 深度代理导致性能问题
  const chart = shallowRef(null)
  let resizeObserver = null

  /**
   * 初始化图表实例
   */
  function init() {
    if (!containerRef.value || chart.value) return
    chart.value = echarts.init(containerRef.value)
  }

  onMounted(() => {
    init()

    // 监听容器尺寸变化（例如侧边栏折叠、窗口缩放），自动重绘图表
    if (containerRef.value && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => resize())
      resizeObserver.observe(containerRef.value)
    }
  })

  onBeforeUnmount(() => {
    // 销毁实例，释放内存，避免页面来回切换时内存泄漏
    resizeObserver?.disconnect()
    resizeObserver = null
    chart.value?.dispose()
    chart.value = null
  })

  /**
   * 设置图表数据
   * @param {object} option ECharts 配置项
   * @param {boolean} notMerge 是否完全替换旧配置，默认 true
   */
  function setOption(option, notMerge = true) {
    if (!chart.value) init()
    chart.value?.setOption(option, notMerge)
  }

  /**
   * 显示加载动画（数据请求期间使用）
   */
  function showLoading() {
    chart.value?.showLoading('default', {
      text: '加载中',
      color: '#2a78d6',
      textColor: '#5c6470',
      maskColor: 'rgba(255, 255, 255, 0.85)',
      zlevel: 0,
    })
  }

  /**
   * 隐藏加载动画
   */
  function hideLoading() {
    chart.value?.hideLoading()
  }

  /**
   * 重新计算图表尺寸
   */
  function resize() {
    chart.value?.resize()
  }

  return { setOption, showLoading, hideLoading, resize }
}
