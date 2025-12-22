import { createRouter, createWebHistory } from 'vue-router';
import { authAPI } from '../api/auth';
import CourseList from '../views/CourseList.vue';
import CourseForm from '../views/CourseForm.vue';

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/courses',
    name: 'CourseList',
    component: CourseList
  },
  {
    path: '/courses/new',
    name: 'CreateCourse',
    component: CourseForm
  },
  {
    path: '/courses/:id/edit',
    name: 'EditCourse',
    component: CourseForm,
    props: true
  },
  {
    path: '/members',
    name: 'MemberList',
    component: () => import('../views/MemberList.vue')
  },
  {
    path: '/payments',
    name: 'PaymentList',
    component: () => import('../views/PaymentList.vue')
  }
];

// 路由守卫实现权限控制
const requireAuth = (to, from, next) => {
  const token = localStorage.getItem('authToken');
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  
  // 需要登录的路由
  const protectedRoutes = ['CreateCourse', 'EditCourse', 'MemberList', 'PaymentList', 'CreatePayment', 'EditPayment'];
  
  if (protectedRoutes.includes(to.name)) {
    if (!token) {
      next('/login');
      return;
    }
    
    // 检查管理员权限的路由
    const adminRoutes = ['CreateCourse', 'EditCourse', 'MemberList', 'CreatePayment', 'EditPayment'];
    if (adminRoutes.includes(to.name) && user.role !== 'admin') {
      next('/');
      return;
    }
  }
  
  next();
};


const router = createRouter({
  history: createWebHistory(),
  routes
});

// 应用路由守卫
router.beforeEach(requireAuth);

export default router;

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
,
  {
    path: '/payments/new',
    name: 'CreatePayment',
    component: () => import('../views/PaymentForm.vue')
  },
  {
    path: '/payments/:id/edit',
    name: 'EditPayment',
    component: () => import('../views/PaymentForm.vue'),
    props: true
  }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
,
  {
    path: '/payments/new',
    name: 'CreatePayment',
    component: () => import('../views/PaymentForm.vue')
  },
  {
    path: '/payments/:id/edit',
    name: 'EditPayment',
    component: () => import('../views/PaymentForm.vue'),
    props: true
  }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
,
  {
    path: '/payments/new',
    name: 'CreatePayment',
    component: () => import('../views/PaymentForm.vue')
  },
  {
    path: '/payments/:id/edit',
    name: 'EditPayment',
    component: () => import('../views/PaymentForm.vue'),
    props: true
  }