/**
 * 路由配置
 *
 * 系统分为两套界面：
 *   管理员（role=admin）：统计首页、用户管理、知识库管理、文档管理、问答记录、智能问答
 *   普通用户（role=user）：智能问答、个人中心
 *
 * 路由守卫会校验登录状态与角色权限。
 */
import { createRouter, createWebHistory } from 'vue-router'

import { TOKEN_KEY, USER_KEY, ROLE_ADMIN } from '@/utils/constants'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录' },
  },

  /* ---------------- 管理员端 ---------------- */
  {
    path: '/admin',
    component: () => import('@/layout/AdminLayout.vue'),
    redirect: '/admin/home',
    meta: { requiresAuth: true, role: ROLE_ADMIN },
    children: [
      {
        path: 'home',
        name: 'AdminHome',
        component: () => import('@/views/admin/Home.vue'),
        meta: { title: '数据总览', icon: 'DataLine' },
      },
      {
        path: 'user',
        name: 'UserManage',
        component: () => import('@/views/admin/UserManage.vue'),
        meta: { title: '用户管理', icon: 'User' },
      },
      {
        path: 'kb',
        name: 'KbManage',
        component: () => import('@/views/admin/KbManage.vue'),
        meta: { title: '知识库管理', icon: 'Collection' },
      },
      {
        path: 'doc',
        name: 'DocManage',
        component: () => import('@/views/admin/DocManage.vue'),
        meta: { title: '文档管理', icon: 'Document' },
      },
      {
        path: 'records',
        name: 'ChatRecords',
        component: () => import('@/views/admin/ChatRecords.vue'),
        meta: { title: '问答记录', icon: 'ChatLineSquare' },
      },
      {
        path: 'chat',
        name: 'AdminChat',
        component: () => import('@/views/user/Chat.vue'),
        meta: { title: '智能问答', icon: 'MagicStick' },
      },
    ],
  },

  /* ---------------- 普通用户端 ---------------- */
  {
    path: '/',
    component: () => import('@/layout/UserLayout.vue'),
    redirect: '/chat',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/user/Chat.vue'),
        meta: { title: '智能问答', icon: 'MagicStick' },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/user/Profile.vue'),
        meta: { title: '个人中心', icon: 'Setting' },
      },
    ],
  },

  // 未匹配到的地址统一跳回首页
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * 全局前置守卫：登录校验 + 角色校验
 *
 * 判断逻辑：
 *   1. 没登录且目标页需要登录 → 跳转登录页，并记录来源地址
 *   2. 已登录但访问登录页 → 直接跳到他对应的首页
 *   3. 角色不匹配 → 跳回自己角色的首页，避免普通用户看到管理后台
 */
router.beforeEach((to, from, next) => {
  // 设置浏览器标签页标题
  document.title = to.meta.title ? `${to.meta.title} - 企业知识库问答系统` : '企业知识库问答系统'

  const token = localStorage.getItem(TOKEN_KEY)
  const userInfo = JSON.parse(localStorage.getItem(USER_KEY) || 'null')

  // 1. 未登录
  if (to.meta.requiresAuth && !token) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  // 2. 已登录还想去登录页 → 按角色送到对应的首页
  if (to.path === '/login' && token) {
    return next(userInfo?.role === ROLE_ADMIN ? '/admin/home' : '/chat')
  }

  // 3. 角色校验：管理员端路由要求 role=admin
  if (to.meta.role === ROLE_ADMIN && userInfo?.role !== ROLE_ADMIN) {
    return next('/chat')
  }

  next()
})

export default router
