// 应用入口文件：创建 Vue 应用并装配路由、状态管理、UI 组件库
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

// Element Plus 样式与自定义全局样式
import 'element-plus/dist/index.css'
import './styles/index.css'

const app = createApp(App)

// 全局注册 Element Plus 的所有图标组件，模板中可直接使用 <el-icon><Search /></el-icon>
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

app.use(createPinia())          // 状态管理
app.use(router)                 // 路由
app.use(ElementPlus, { locale: zhCn })  // UI 组件库，使用中文语言包

app.mount('#app')
