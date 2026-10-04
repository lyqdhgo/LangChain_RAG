<script setup>
/**
 * Markdown 渲染组件
 *
 * 大模型的回答通常是 Markdown 格式（标题、列表、加粗、代码块等），
 * 直接当纯文本显示会很难看，所以这里用 marked 转成 HTML。
 *
 * 安全提示：模型输出属于「不可信内容」，必须经过 DOMPurify 过滤后再渲染，
 * 否则可能被注入恶意脚本（XSS）。
 */
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  // Markdown 原文
  content: {
    type: String,
    default: '',
  },
})

// marked 基础配置：开启换行转 <br>，让回答更贴近模型原本的排版意图
marked.setOptions({
  breaks: true,
  gfm: true,
})

// 把 Markdown 转成安全的 HTML
const html = computed(() => {
  if (!props.content) return ''
  const raw = marked.parse(props.content)
  return DOMPurify.sanitize(raw)
})
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="markdown-body" v-html="html"></div>
</template>

<style scoped>
.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--app-text-primary);
  word-break: break-word;
}

/* 下面用 :deep() 穿透作用域，给 v-html 生成的内容设置样式 */

.markdown-body :deep(p) {
  margin: 0 0 10px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 16px 0 8px;
  font-weight: 600;
  line-height: 1.4;
}

.markdown-body :deep(h1) { font-size: 18px; }
.markdown-body :deep(h2) { font-size: 16px; }
.markdown-body :deep(h3) { font-size: 15px; }
.markdown-body :deep(h4) { font-size: 14px; }

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0 0 10px;
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin-bottom: 4px;
}

.markdown-body :deep(code) {
  background-color: #f2f3f5;
  border-radius: 3px;
  padding: 1px 5px;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 13px;
  color: #c7254e;
}

.markdown-body :deep(pre) {
  background-color: #f6f8fa;
  border: 1px solid var(--app-border);
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin: 0 0 10px;
}

.markdown-body :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: var(--app-text-primary);
}

.markdown-body :deep(blockquote) {
  margin: 0 0 10px;
  padding: 6px 12px;
  border-left: 3px solid #409eff;
  background-color: #f7f9fc;
  color: var(--app-text-secondary);
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0 0 10px;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--app-border);
  padding: 6px 10px;
  text-align: left;
}

.markdown-body :deep(th) {
  background-color: #fafafa;
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: #2a78d6;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--app-border);
  margin: 16px 0;
}

.markdown-body :deep(img) {
  max-width: 100%;
}
</style>
