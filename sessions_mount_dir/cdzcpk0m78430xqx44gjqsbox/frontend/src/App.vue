<script setup>
import { RouterView } from 'vue-router'
import HelloWorld from './components/HelloWorld.vue'
</script>

<template>
  <div class="app-container">
    <header>
      <nav>
        <router-link to="/members">会员管理</router-link>
        <router-link to="/courses">课程预约</router-link>
        <router-link to="/coaches">教练管理</router-link>
        <router-link to="/coaches/schedules">教练排班</router-link>
        <router-link to="/payments">收费记录</router-link>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

header {
  background-color: #f8f9fa;
  padding: 1rem 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

nav {
  margin: 0 auto;
  max-width: 1200px;
  padding: 0 2rem;
}

nav a {
  margin-right: 1rem;
  color: #42b883;
  text-decoration: none;
}

nav a:hover {
  text-decoration: underline;
}
</style>
