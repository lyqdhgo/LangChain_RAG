<script setup>
/**
 * 普通用户端整体布局
 *
 * 比管理端更简洁：顶部横向导航 + 内容区，移动端也能正常使用。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 顶部导航菜单
const menus = [
  { path: '/chat', title: '智能问答', icon: 'MagicStick' },
  { path: '/profile', title: '个人中心', icon: 'Setting' },
]

const currentTitle = computed(() => route.meta.title || '智能问答')

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
    return
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
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<template>
  <div class="user-layout">
    <!-- ==================== 顶部导航 ==================== -->
    <header class="navbar">
      <div class="navbar-inner">
        <!-- Logo -->
        <div class="logo">
          <el-icon class="logo-icon"><Reading /></el-icon>
          <span class="logo-text">企业知识库问答</span>
        </div>

        <!-- 导航菜单 -->
        <nav class="nav-menu">
          <router-link
            v-for="item in menus"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: route.path === item.path }"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </router-link>
        </nav>

        <!-- 用户信息 -->
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
              <el-dropdown-item command="profile">
                <el-icon><Setting /></el-icon>个人中心
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- ==================== 内容区 ==================== -->
    <main class="content">
      <router-view v-slot="{ Component }">
        <keep-alive :max="3">
          <component :is="Component" :key="route.path" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.user-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* ---------- 顶部导航 ---------- */
.navbar {
  background-color: #fff;
  border-bottom: 1px solid var(--app-border);
  flex-shrink: 0;
}

.navbar-inner {
  display: flex;
  align-items: center;
  gap: 32px;
  height: 60px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 600;
  color: var(--app-text-primary);
  white-space: nowrap;
}

.logo-icon {
  font-size: 22px;
  color: #409eff;
}

.nav-menu {
  display: flex;
  gap: 8px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  color: var(--app-text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-item:hover {
  background-color: #f5f7fa;
  color: #409eff;
}

.nav-item.active {
  background-color: #ecf5ff;
  color: #409eff;
  font-weight: 500;
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
.content {
  flex: 1;
  overflow: hidden;
  background-color: var(--app-page-bg);
}
</style>
