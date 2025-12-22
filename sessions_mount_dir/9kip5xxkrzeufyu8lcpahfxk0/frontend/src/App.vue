<script setup>
const { locale } = useI18n()
import { RouterLink, RouterView } from 'vue-router'
import HelloWorld from './components/HelloWorld.vue'
import { useI18n } from 'vue-i18n'
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <div class="wrapper">
        <nav class="app-nav">
          <div class="nav-content">
            <select v-model="locale" class="language-select">
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
            <div class="nav-links">
              <RouterLink to="/" class="nav-link">首页</RouterLink>
              <RouterLink to="/courses" class="nav-link">课程预约</RouterLink>
              <RouterLink to="/coaches/schedules" class="nav-link">教练排班</RouterLink>
              <RouterLink to="/payments" class="nav-link">收费管理</RouterLink>
            </div>
          </div>
        </nav>
      </div>
    </header>

    <main class="main-content">
      <div class="router-view-container">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  background-color: var(--color-background-soft);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1rem 0;
}

.app-nav {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.nav-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-links {
  display: flex;
  gap: 1rem;
}

.nav-link {
  padding: 0.5rem 1rem;
  text-decoration: none;
  color: var(--color-text);
  transition: all 0.3s ease;
  border-radius: 4px;
}

.nav-link:hover {
  color: var(--color-primary);
  background-color: var(--color-background-mute);
}

.nav-link.router-link-exact-active {
  color: var(--color-primary);
  font-weight: 500;
}

.main-content {
  flex: 1;
  padding: 2rem 1rem;
}

.router-view-container {
  max-width: 1200px;
  margin: 0 auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<style>
.language-select {
  margin-left: 1rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
}
</style>