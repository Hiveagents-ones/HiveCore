import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import axios from 'axios'

// 配置axios默认baseURL
axios.defaults.baseURL = '/api/v1'

createApp(App).mount('#app')