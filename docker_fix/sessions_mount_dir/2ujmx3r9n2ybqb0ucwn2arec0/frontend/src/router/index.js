import { createRouter, createWebHistory } from 'vue-router'
import CourseListView from '../views/CourseListView.vue'
import CourseDetailView from '../views/CourseDetailView.vue'

const routes = [
  {
    path: '/',
    redirect: '/courses'
  },
  {
    path: '/courses',
    name: 'CourseList',
    component: CourseListView,
    meta: {
      title: '课程列表'
    }
  },
  {
    path: '/courses/:id',
    name: 'CourseDetail',
    component: CourseDetailView,
    props: true,
    meta: {
      title: '课程详情'
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