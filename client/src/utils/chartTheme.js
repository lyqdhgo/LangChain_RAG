/**
 * ECharts 图表通用配置
 *
 * 把颜色、字体、坐标轴样式等统一收敛到这里，保证首页所有图表风格一致，
 * 后续要换配色只需要改这一处。
 *
 * 配色说明：
 *   下面 SERIES_COLORS 的 8 个色槽经过色盲友好度校验，必须按固定顺序取用，
 *   不要跳着取色，也不要循环复用（第 9 个系列应该合并成"其他"）。
 */

// 分类配色（按顺序使用）
export const SERIES_COLORS = [
  '#2a78d6', // 1 蓝
  '#eb6834', // 2 橙
  '#1baf7a', // 3 青
  '#eda100', // 4 黄
  '#e87ba4', // 5 品红
  '#008300', // 6 绿
  '#4a3aa7', // 7 紫
  '#e34948', // 8 红
]

// 状态色：专门用来表达"状态"，不参与普通系列的取色
export const STATUS_COLORS = {
  pending: '#8a9099',    // 待处理（中性灰，表示排队中）
  processing: '#fab219', // 向量化中（黄）
  success: '#0ca30c',    // 已完成（绿）
  failed: '#d03b3b',     // 失败（红）
}

// 图表文字与线条颜色
const INK = {
  primary: '#1f2329',
  secondary: '#5c6470',
  muted: '#8a9099',
  grid: '#e9e9e4',
  axis: '#c3c2b7',
}

// 统一的字体族，和页面保持一致
const FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif"

/**
 * 生成基础配置项（所有图表共用）
 *
 * @param {object} options 可选配置
 * @param {boolean} options.showLegend 是否显示图例（两个及以上系列才需要）
 * @returns {object} ECharts 基础 option
 */
export function baseOption({ showLegend = false } = {}) {
  return {
    // 配色：按顺序取用
    color: SERIES_COLORS,
    textStyle: {
      fontFamily: FONT_FAMILY,
      color: INK.secondary,
    },
    // 图例：两个及以上系列时必须有图例，保证不靠颜色单独区分数据
    legend: showLegend
      ? {
          top: 0,
          right: 0,
          icon: 'roundRect',
          itemWidth: 10,
          itemHeight: 10,
          itemGap: 16,
          textStyle: { color: INK.secondary, fontSize: 12 },
        }
      : { show: false },
    // 提示框：鼠标悬停时展示详细数值
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: INK.axis, type: 'dashed' } },
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: INK.primary, fontSize: 12 },
      extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.12); border-radius: 6px;',
    },
    grid: {
      top: showLegend ? 40 : 20,
      left: 8,
      right: 16,
      bottom: 4,
      containLabel: true,
    },
  }
}

/**
 * 生成类目轴（X 轴）配置
 * @param {string[]} data 类目数据
 */
export function categoryAxis(data) {
  return {
    type: 'category',
    data,
    // 轴线与刻度尽量弱化，让数据本身更突出
    axisLine: { lineStyle: { color: INK.axis } },
    axisTick: { show: false },
    axisLabel: { color: INK.muted, fontSize: 12 },
  }
}

/**
 * 生成数值轴（Y 轴）配置
 */
export function valueAxis() {
  return {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    // 只保留横向网格线，且颜色很浅，避免干扰数据
    splitLine: { lineStyle: { color: INK.grid } },
    axisLabel: { color: INK.muted, fontSize: 12 },
  }
}

/**
 * 生成折线系列的配置
 *
 * @param {string} name 系列名称
 * @param {number[]} data 数据
 * @param {number} colorIndex 取第几个色槽（从 0 开始）
 * @param {boolean} smooth 是否平滑曲线
 */
export function lineSeries(name, data, colorIndex = 0, smooth = true) {
  return {
    name,
    type: 'line',
    data,
    smooth,
    symbol: 'circle',
    symbolSize: 8,          // 数据点直径不小于 8px，方便鼠标悬停
    lineStyle: { width: 2 }, // 线条保持 2px，细而清晰
    itemStyle: { color: SERIES_COLORS[colorIndex] },
    emphasis: { focus: 'series', scale: 1.2 },
  }
}

/**
 * 生成柱状系列的配置
 *
 * @param {string} name 系列名称
 * @param {number[]} data 数据
 * @param {number} colorIndex 取第几个色槽（从 0 开始）
 * @param {boolean} horizontal 是否是横向柱状图
 */
export function barSeries(name, data, colorIndex = 0, horizontal = false) {
  return {
    name,
    type: 'bar',
    data,
    // 柱子保持细一些，顶端做 4px 圆角
    barMaxWidth: 28,
    itemStyle: {
      color: SERIES_COLORS[colorIndex],
      borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
    },
    emphasis: { focus: 'series' },
  }
}

/**
 * 生成饼图 / 环形图的配置
 *
 * 饼图默认不显示图例，改为在扇区上直接标注名称与占比
 * （直接标注比图例更直观，也满足低对比度颜色的可读性要求）。
 *
 * @param {Array<{name: string, value: number}>} data 数据
 * @param {string[]} colors 使用的颜色数组
 * @param {boolean} donut 是否显示成环形图
 */
export function pieSeries(data, colors, donut = false) {
  return {
    type: 'pie',
    data,
    radius: donut ? ['45%', '68%'] : ['0%', '68%'],
    center: ['50%', '52%'],
    // 每个扇区之间留出 2px 的白边，视觉上更清晰
    itemStyle: { borderColor: '#ffffff', borderWidth: 2, borderRadius: 4 },
    label: {
      show: true,
      formatter: '{b}\n{d}%',
      color: INK.secondary,
      fontSize: 12,
      lineHeight: 16,
    },
    labelLine: { length: 10, length2: 12, lineStyle: { color: INK.axis } },
    emphasis: {
      scaleSize: 6,
      label: { color: INK.primary, fontWeight: 'bold' },
    },
    // 按传入的颜色数组取色
    color: colors,
  }
}

// 导出文字颜色，供表格等地方复用
export { INK }
