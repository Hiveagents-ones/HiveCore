import { createRouter, createWebHistory } from 'vue-router';
import MemberList from '../views/MemberList.vue';
import MemberDetail from '../views/MemberDetail.vue';
import MemberForm from '../views/MemberForm.vue';

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
      title: '会员列表'
    }
  },
  {
    path: '/members/new',
    name: 'MemberCreate',
    component: MemberForm,
    meta: {
      title: '新增会员'
    }
  },
  {
    path: '/members/:id',
    name: 'MemberDetail',
    component: MemberDetail,
    meta: {
      title: '会员详情'
    }
  },
  {
    path: '/members/:id/edit',
    name: 'MemberEdit',
    component: MemberForm,
    meta: {
      title: '编辑会员'
    }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 会员管理系统` : '会员管理系统';
  next();
});

export default router;