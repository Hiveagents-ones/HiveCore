import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 路由组件懒加载
const Login = () => import('@/views/Login.vue')
const Dashboard = () => import('@/views/Dashboard.vue')
const MemberList = () => import('@/views/member/MemberList.vue')
const MemberDetail = () => import('@/views/member/MemberDetail.vue')
const MemberCreate = () => import('@/views/member/MemberCreate.vue')
const CourseList = () => import('@/views/CourseList.vue')
const Renewal = () => import('@/views/Renewal.vue')
const PaymentHistory = () => import('@/views/PaymentHistory.vue')
const NotFound = () => import('@/views/NotFound.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false, title: '登录' }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true, title: '仪表盘' }
  },
  {
    path: '/members',
    name: 'MemberList',
    component: MemberList,
    meta: { requiresAuth: true, title: '会员列表' }
  },
  {
    path: '/members/create',
    name: 'MemberCreate',
    component: MemberCreate,
    meta: { requiresAuth: true, title: '创建会员' }
  },
  {
    path: '/members/:id',
    name: 'MemberDetail',
    component: MemberDetail,
    meta: { requiresAuth: true, title: '会员详情' },
    props: true
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
    meta: { title: '页面未找到' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 会员管理系统` : '会员管理系统'
  
  // 检查是否需要认证
  if (to.meta.requiresAuth) {
    // 如果未登录，重定向到登录页
    if (!authStore.isAuthenticated) {
      next({
        name: 'Login',
        query: { redirect: to.fullPath }
      })
      return
    }
    
    // 检查token是否有效
    if (authStore.token && !authStore.user) {
      try {
        await authStore.fetchUserInfo()
      } catch (error) {
        console.error('获取用户信息失败:', error)
        authStore.logout()
        next({
          name: 'Login',
          query: { redirect: to.fullPath }
        })
        return
      }
    }
  }
  
  // 如果已登录且访问登录页，重定向到仪表盘
  if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
    return
  }
  
  next()
})

export default router

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
  {
    path: '/courses',
    name: 'CourseList',
    component: CourseList,
    meta: { requiresAuth: true, title: '课程列表' }
  },

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
  {
    path: '/courses',
    name: 'CourseList',
    component: CourseList,
    meta: { requiresAuth: true, title: '课程列表' }
  },
  {
    path: '/renewal',
    name: 'Renewal',
    component: Renewal,
    meta: { requiresAuth: true, title: '续费管理' }
  },
  {
    path: '/payment-history',
    name: 'PaymentHistory',
    component: PaymentHistory,
    meta: { requiresAuth: true, title: '支付历史' }
  },

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
  {
    path: '/courses',
    name: 'CourseList',
    component: CourseList,
    meta: { requiresAuth: true, title: '课程列表' }
  },
  {
    path: '/renewal',
    name: 'Renewal',
    component: Renewal,
    meta: { requiresAuth: true, title: '续费管理' }
  },
  {
    path: '/payment-history',
    name: 'PaymentHistory',
    component: PaymentHistory,
    meta: { requiresAuth: true, title: '支付历史' }
  },

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
  {
    path: '/courses',
    name: 'CourseList',
    component: CourseList,
    meta: { requiresAuth: true, title: '课程列表' }
  },
  {
    path: '/renewal',
    name: 'Renewal',
    component: Renewal,
    meta: { requiresAuth: true, title: '续费管理' }
  },
  {
    path: '/payment-history',
    name: 'PaymentHistory',
    component: PaymentHistory,
    meta: { requiresAuth: true, title: '支付历史' }
  },