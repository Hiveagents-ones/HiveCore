import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 路由组件懒加载
const AdminLayout = () => import('@/layouts/AdminLayout.vue')
const MemberLayout = () => import('@/layouts/MemberLayout.vue')
const Login = () => import('@/views/Login.vue')
const Dashboard = () => import('@/views/Dashboard.vue')

// 管理员路由
const CourseManagement = () => import('@/views/admin/CourseManagement.vue')
const CoachManagement = () => import('@/views/admin/CoachManagement.vue')
const MemberManagement = () => import('@/views/admin/MemberManagement.vue')
const BookingManagement = () => import('@/views/admin/BookingManagement.vue')

// 会员路由
const CourseSchedule = () => import('@/views/member/CourseSchedule.vue')
const MyBookings = () => import('@/views/member/MyBookings.vue')
const Profile = () => import('@/views/member/Profile.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      {
        path: 'courses',
        name: 'AdminCourseManagement',
        component: CourseManagement,
        meta: { title: '课程管理' }
      },
      {
        path: 'coaches',
        name: 'AdminCoachManagement',
        component: CoachManagement,
        meta: { title: '教练管理' }
      },
      {
        path: 'members',
        name: 'AdminMemberManagement',
        component: MemberManagement,
        meta: { title: '会员管理' }
      },
      {
        path: 'bookings',
        name: 'AdminBookingManagement',
        component: BookingManagement,
        meta: { title: '预约管理' }
      }
    ]
  },
  {
    path: '/member',
    component: MemberLayout,
    meta: { requiresAuth: true, role: 'member' },
    children: [
      {
        path: 'schedule',
        name: 'MemberCourseSchedule',
        component: CourseSchedule,
        meta: { title: '课程表' }
      },
      {
        path: 'bookings',
        name: 'MemberMyBookings',
        component: MyBookings,
        meta: { title: '我的预约' }
      },
      {
        path: 'profile',
        name: 'MemberProfile',
        component: Profile,
        meta: { title: '个人资料' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const requiredRole = to.meta.role

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (requiredRole && authStore.userRole !== requiredRole) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router