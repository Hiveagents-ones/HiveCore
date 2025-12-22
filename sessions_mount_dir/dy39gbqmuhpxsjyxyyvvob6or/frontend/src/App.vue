<script setup>
import { RouterView } from 'vue-router'
</script>

<template>
  <div id="app" class="app-container">
    <nav class="navbar">
      <router-link to="/members">会员管理</router-link>
      <router-link to="/courses">课程预约</router-link>
      <router-link to="/coaches">教练排班</router-link>
      <router-link to="/payments">收费管理</router-link>
    </nav>
    <router-view />
  </div>
</template>

<style scoped>
.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}
.navbar {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 4px;
}
.navbar a {
  color: #2c3e50;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
}
.navbar a:hover {
  background: #e0e0e0;
}
.navbar a.router-link-exact-active {
  color: white;
  background: #42b883;
}
</style>
