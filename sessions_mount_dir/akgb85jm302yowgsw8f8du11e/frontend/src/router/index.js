import { createRouter, createWebHistory } from 'vue-router';
import CourseListView from '../views/CourseListView.vue';

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
      title: '课程预约'
    }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to, from, next) => {
  document.title = to.meta.title || '健身房管理系统';
  next();
});

export default router;