import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import router from './router'
import { messages } from './locales'
import './assets/main.css'

// 创建 i18n 实例
const i18n = createI18n({
  legacy: false,
  locale: 'zh', // 默认语言
  fallbackLocale: 'en', // 回退语言
  messages,
})

// 创建 Vue 应用实例
const app = createApp(App)

// 使用插件
app.use(createPinia())
app.use(router)
app.use(i18n)

// 挂载应用
app.mount('#app')