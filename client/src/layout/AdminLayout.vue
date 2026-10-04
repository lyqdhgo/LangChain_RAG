<script setup>
/**
 * 管理员端整体布局
 *
 * 结构：左侧菜单 + 顶部栏 + 右侧内容区
 * 左侧菜单根据当前路由自动高亮，顶部栏显示面包屑与用户下拉菜单。
 */
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 侧边栏是否折叠
const isCollapse = ref(false)

// 管理员菜单配置（与路由表中的子路由一一对应）
const menus = [
  { path: '/admin/home', title: '数据总览', icon: 'DataLine' },
  { path: '/admin/user', title: '用户管理', icon: 'User' },
  { path: '/admin/kb', title: '知识库管理', icon: 'Collection' },
  { path: '/admin/doc', title: '文档管理', icon: 'Document' },
  { path: '/admin/records', title: '问答记录', icon: 'ChatLineSquare' },
  { path: '/admin/chat', title: '智能问答', icon: 'MagicStick' },
]

// 当前页面标题，用于顶部面包屑
const currentTitle = computed(() => route.meta.title || '数据总览')

/**
 * 退出登录
 */
async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return // 用户点击了取消
  }

  await userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

/**
 * 用户下拉菜单点击处理
 * @param {string} command 菜单指令
 */
function handleCommand(command) {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'chat') {
    router.push('/admin/chat')
  }
}
</script>

<template>
  <el-container class="admin-layout">
    <!-- ==================== 左侧菜单 ==================== -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <!-- 系统 Logo -->
      <div class="logo">
        <el-icon class="logo-icon"><Reading /></el-icon>
        <span v-show="!isCollapse" class="logo-text">企业知识库问答</span>
      </div>

      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        background-color="#1f2733"
        text-color="#bfcbd9"
        active-text-color="#ffffff"
      >
        <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- ==================== 顶部栏 ==================== -->
      <el-header class="header">
        <div class="header-left">
          <!-- 折叠按钮 -->
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>管理后台</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-tag type="success" effect="plain" size="small">管理员</el-tag>

          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="30" class="avatar">
                {{ userStore.displayName.charAt(0) }}
              </el-avatar>
              <span class="username">{{ userStore.displayName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="chat">
                  <el-icon><MagicStick /></el-icon>去提问
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- ==================== 内容区 ==================== -->
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <keep-alive :max="5">
            <component :is="Component" :key="route.path" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  height: 100vh;
}

/* ---------- 侧边栏 ---------- */
.sidebar {
  background-color: #1f2733;
  transition: width 0.25s;
  overflow-x: hidden;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 60px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-icon {
  font-size: 22px;
  color: #409eff;
}

.sidebar :deep(.el-menu) {
  border-right: none;
}

.sidebar :deep(.el-menu-item.is-active) {
  background-color: #409eff !important;
}

.sidebar :deep(.el-menu-item:hover) {
  background-color: #2b3648 !important;
}

/* ---------- 顶部栏 ---------- */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  background-color: #fff;
  border-bottom: 1px solid var(--app-border);
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: var(--app-text-secondary);
}

.collapse-btn:hover {
  color: #409eff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  outline: none;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.avatar {
  background-color: #409eff;
  color: #fff;
  font-size: 14px;
}

.username {
  font-size: 14px;
  color: var(--app-text-primary);
}

/* ---------- 内容区 ---------- */
.main {
  padding: 16px;
  background-color: var(--app-page-bg);
  overflow-y: auto;
}
</style>
