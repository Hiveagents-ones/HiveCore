import { createRouter, createWebHistory } from 'vue-router'
import MemberManagement from '../views/MemberManagement.vue'

const routes = [
  {
    path: '/',
    redirect: '/members'
  },
  {
    path: '/members',
    name: 'MemberManagement',
    component: MemberManagement,
    meta: {
      title: '会员管理'
    }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router