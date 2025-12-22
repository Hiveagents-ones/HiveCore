import { createRouter, createWebHistory } from 'vue-router'
import MemberList from '../views/MemberList.vue'
import MemberDetail from '../views/MemberDetail.vue'
import MemberCreate from '../views/MemberCreate.vue'
import MemberEdit from '../views/MemberEdit.vue'
import CourseSchedule from '../views/CourseSchedule.vue'
import CoachList from '../views/CoachList.vue'
import CoachDetail from '../views/CoachDetail.vue'
import CoachCreate from '../views/CoachCreate.vue'
import CoachEdit from '../views/CoachEdit.vue'

const routes = [
  {
    path: '/',
    redirect: '/members'
  },
  {
    path: '/members',
    name: 'MemberList',
    component: MemberList,
    meta: {
      title: '会员列表',
      requiresAuth: true
    }
  },
  {
    path: '/members/create',
    name: 'MemberCreate',
    component: MemberCreate,
    meta: {
      title: '创建会员',
      requiresAuth: true
    }
  },
  {
    path: '/members/:id',
    name: 'MemberDetail',
    component: MemberDetail,
    meta: {
      title: '会员详情',
      requiresAuth: true
    }
  },
  {
    path: '/members/:id/edit',
    name: 'MemberEdit',
    component: MemberEdit,
    meta: {
      title: '编辑会员',
      requiresAuth: true
    }
  },
  {
    path: '/courses',
    name: 'CourseSchedule',
    component: CourseSchedule,
    meta: {
      title: '课程表',
      requiresAuth: true
    }
  },
  {
    path: '/coaches',
    name: 'CoachList',
    component: CoachList,
    meta: {
      title: '教练列表',
      requiresAuth: true
    }
  },
  {
    path: '/coaches/create',
    name: 'CoachCreate',
    component: CoachCreate,
    meta: {
      title: '创建教练',
      requiresAuth: true
    }
  },
  {
    path: '/coaches/:id',
    name: 'CoachDetail',
    component: CoachDetail,
    meta: {
      title: '教练详情',
      requiresAuth: true
    }
  },
  {
    path: '/coaches/:id/edit',
    name: 'CoachEdit',
    component: CoachEdit,
    meta: {
      title: '编辑教练',
      requiresAuth: true
    }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 会员管理系统` : '会员管理系统'

  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      next('/login')
      return
    }
  }

  next()
})

export default router