import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/members',
    name: 'Members',
    component: () => import('@/views/members/MemberList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/members/create',
    name: 'CreateMember',
    component: () => import('@/views/members/MemberForm.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/members/:id/edit',
    name: 'EditMember',
    component: () => import('@/views/members/MemberForm.vue'),
    meta: { requiresAuth: true },
    props: true
  },
  {
    path: '/members/:id',
    name: 'MemberDetail',
    component: () => import('@/views/members/MemberDetail.vue'),
    meta: { requiresAuth: true },
    props: true
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

// Navigation guards
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const isAuthenticated = authStore.isAuthenticated

  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.guest && isAuthenticated) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router