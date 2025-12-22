import { createRouter, createWebHistory } from 'vue-router'
import CourseList from '@/views/CourseList.vue'
import MyBookings from '@/views/MyBookings.vue'

const routes = [
  {
    path: '/',
    redirect: '/courses'
  },
  {
    path: '/courses',
    name: 'CourseList',
    component: CourseList,
    meta: {
      title: '课程列表'
    }
  },
  {
    path: '/my-bookings',
    name: 'MyBookings',
    component: MyBookings,
    meta: {
      title: '我的预约'
    }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 健身房预约系统` : '健身房预约系统'
  next()
})

export default router