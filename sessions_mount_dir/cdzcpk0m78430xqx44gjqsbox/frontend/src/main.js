import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import './style.css'
import App from './App.vue'
import { useCoachesStore } from './stores/coaches'
import { useMembersStore } from './stores/members'
import { usePaymentsStore } from './stores/payments'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/members', component: () => import('./views/MembersView.vue') },
    { path: '/courses', component: () => import('./views/CoursesView.vue') },
    { path: '/coaches', component: () => import('./views/CoachesView.vue') },
    { path: '/payments', component: () => import('./views/PaymentsView.vue') },
    { path: '/', redirect: '/courses' }
  ]
})

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Initialize stores
const coachesStore = useCoachesStore()
const membersStore = useMembersStore()
const paymentsStore = usePaymentsStore()

coachesStore.fetchCoaches()
membersStore.fetchMembers()
paymentsStore.fetchPayments()

app.mount('#app')