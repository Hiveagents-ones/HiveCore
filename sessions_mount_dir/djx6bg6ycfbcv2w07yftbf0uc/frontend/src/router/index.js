import { createRouter, createWebHistory } from 'vue-router'
import MemberList from '../views/MemberList.vue'
import MemberDetail from '../views/MemberDetail.vue'
import TagManager from '../components/TagManager.vue'
import NoteManager from '../components/NoteManager.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/members',
    name: 'MemberList',
    component: MemberList,
    meta: {
      title: '会员管理',
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
    },
    children: [
      {
        path: 'tags',
        name: 'MemberTags',
        component: TagManager,
        meta: {
          title: '标签管理'
        }
      },
      {
        path: 'notes',
        name: 'MemberNotes',
        component: NoteManager,
        meta: {
          title: '备注管理'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 商家端` : '商家端'
  
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      next('/login')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router