import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// 初始化Pinia状态管理
const pinia = createPinia()

// 路由守卫配置
router.beforeEach((to, from, next) => {
  // 这里可以添加权限验证等逻辑
  next()
})

// 确保Pinia在路由之前初始化
app.use(pinia)

// 初始化路由
router.isReady().then(() => {
  // 按正确顺序注册插件
  app.use(router)
  app.use(ElementPlus)
  
  app.mount('#app')
})
