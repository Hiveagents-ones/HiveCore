import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createI18n } from 'vue-i18n'
import router from './router'
import './style.css'
import App from './App.vue'

const i18n = createI18n({
  locale: 'zh-CN',
  fallbackLocale: 'en',
  messages: {
    'zh-CN': {
      member: {
        title: '会员信息管理',
        name: '姓名',
        contact: '联系方式',
        cardNumber: '会员卡号',
        level: '会员等级',
        remainingTime: '剩余会籍时长'
      }
    },
    'en': {
      member: {
        title: 'Member Information Management',
        name: 'Name',
        contact: 'Contact',
        cardNumber: 'Card Number',
        level: 'Member Level',
        remainingTime: 'Remaining Membership Time'
      }
    }
  }
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.use(i18n)

app.mount('#app')