import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'

// Layouts
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'

// Views
import Login from '@/views/auth/Login.vue'
import Dashboard from '@/views/Dashboard.vue'
import MemberList from '@/views/members/MemberList.vue'
import MemberDetail from '@/views/members/MemberDetail.vue'
import MemberCreate from '@/views/members/MemberCreate.vue'
import MemberEdit from '@/views/members/MemberEdit.vue'
import NotFound from '@/views/NotFound.vue'

const routes = [
  {
    path: '/auth',
    component: AuthLayout,
    meta: { requiresGuest: true },
    children: [
      {
        path: 'login',
        name: 'Login',
        component: Login,
        meta: { title: 'auth.login' }
      }
    ]
  },
  {
    path: '/',
    component: DefaultLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: 'dashboard.title' }
      },
      {
        path: 'members',
        name: 'MemberList',
        component: MemberList,
        meta: { title: 'members.list' }
      },
      {
        path: 'members/create',
        name: 'MemberCreate',
        component: MemberCreate,
        meta: { title: 'members.create' }
      },
      {
        path: 'members/:id',
        name: 'MemberDetail',
        component: MemberDetail,
        meta: { title: 'members.detail' }
      },
      {
        path: 'members/:id/edit',
        name: 'MemberEdit',
        component: MemberEdit,
        meta: { title: 'members.edit' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
    meta: { title: 'error.notFound' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const { t } = useI18n()
  
  // Initialize auth state if not already done
  if (!authStore.isInitialized) {
    await authStore.initialize()
  }
  
  // Update page title
  if (to.meta.title) {
    document.title = `${t(to.meta.title)} - ${t('app.name')}`
  }
  
  // Check authentication requirements
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router