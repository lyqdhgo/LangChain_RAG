// Vite 构建配置
import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      // 用 @ 指向 src 目录，导入时就不用写一长串相对路径
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    port: 5173,      // 前端开发服务器端口
    open: true,      // 启动后自动打开浏览器
    proxy: {
      // 把 /api 开头的请求转发到 Flask 后端，这样开发时不会遇到跨域问题
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
