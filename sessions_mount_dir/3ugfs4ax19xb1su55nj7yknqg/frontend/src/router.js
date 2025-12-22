import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';

const routes = [
  {
    path: '/',
    name: 'Home',
    component: App
  },
  {
    path: '/courses',
    name: 'Courses',
    component: () => import('./views/CoursesView.vue')
  },
  {
    path: '/courses/:id',
    name: 'CourseDetail',
    component: () => import('./views/CourseDetailView.vue')
  },
  {
    path: '/booking',
    name: 'Booking',
    component: () => import('./views/BookingView.vue')
  },
  {
    path: '/coaches',
    name: 'Coaches',
    component: () => import('./views/CoachesView.vue')
  },
  {
    path: '/coaches/:id',
  {
    path: '/coaches/:id/schedule',
    name: 'CoachSchedule',
    component: () => import('./views/CoachScheduleView.vue')
  },
    name: 'CoachDetail',
    component: () => import('./views/CoachDetailView.vue')
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;