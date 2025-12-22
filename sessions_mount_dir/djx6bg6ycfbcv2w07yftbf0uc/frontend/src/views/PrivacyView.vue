<template>
  <div class="privacy-view">
    <div class="container">
      <h1>隐私政策</h1>
      <p class="last-updated">最后更新时间：{{ lastUpdated }}</p>
      
      <div class="privacy-content">
        <section>
          <h2>1. 信息收集</h2>
          <p>我们收集以下类型的信息：</p>
          <ul>
            <li>账户信息：包括手机号、邮箱、昵称、头像等</li>
            <li>使用信息：包括登录时间、操作记录等</li>
            <li>设备信息：包括设备型号、操作系统版本等</li>
          </ul>
        </section>

        <section>
          <h2>2. 信息使用</h2>
          <p>我们使用收集的信息用于：</p>
          <ul>
            <li>提供和维护我们的服务</li>
            <li>改善用户体验</li>
            <li>发送重要通知</li>
            <li>防范欺诈和滥用</li>
          </ul>
        </section>

        <section>
          <h2>3. 信息共享</h2>
          <p>我们不会向第三方出售、交易或转让您的个人信息，除非：</p>
          <ul>
            <li>获得您的明确同意</li>
            <li>法律要求或法院命令要求</li>
            <li>保护我们的权利、财产或安全</li>
          </ul>
        </section>

        <section>
          <h2>4. 数据安全</h2>
          <p>我们采取适当的安全措施来保护您的个人信息，包括：</p>
          <ul>
            <li>使用SSL加密技术</li>
            <li>定期安全审计</li>
            <li>访问权限控制</li>
          </ul>
        </section>

        <section>
          <h2>5. Cookie使用</h2>
          <p>我们使用Cookie来改善您的浏览体验。您可以通过浏览器设置控制Cookie的使用。</p>
        </section>

        <section>
          <h2>6. 联系我们</h2>
          <p>如果您对本隐私政策有任何疑问，请通过以下方式联系我们：</p>
          <ul>
            <li>邮箱：privacy@example.com</li>
            <li>电话：400-123-4567</li>
          </ul>
        </section>
      </div>

      <div class="actions">
        <button @click="goBack" class="btn btn-secondary">返回</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const lastUpdated = ref('2024-01-01')

const goBack = () => {
  router.go(-1)
}
</script>

<style scoped>
.privacy-view {
  min-height: 100vh;
  background-color: #f5f5f5;
  padding: 20px 0;
}

.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  color: #333;
  margin-bottom: 10px;
  font-size: 2rem;
}

.last-updated {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 30px;
}

.privacy-content {
  line-height: 1.6;
}

section {
  margin-bottom: 30px;
}

h2 {
  color: #444;
  font-size: 1.3rem;
  margin-bottom: 15px;
  padding-bottom: 5px;
  border-bottom: 2px solid #eee;
}

p {
  margin-bottom: 10px;
  color: #555;
}

ul {
  margin-left: 20px;
  margin-bottom: 15px;
}

li {
  margin-bottom: 8px;
  color: #666;
}

.actions {
  margin-top: 40px;
  text-align: center;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #5a6268;
}

@media (max-width: 768px) {
  .container {
    margin: 0 10px;
    padding: 15px;
  }
  
  h1 {
    font-size: 1.5rem;
  }
  
  h2 {
    font-size: 1.1rem;
  }
}
</style>