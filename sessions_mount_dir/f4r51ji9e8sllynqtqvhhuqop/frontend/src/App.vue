<script setup>
import TodoCreate from './views/TodoCreate.vue'
</script>

<template>
  <div id="app">
    <header class="app-header">
      <h1>待办事项管理系统</h1>
    </header>
    <main class="app-main">
      <TodoCreate />
    </main>
  </div>
</template>

<style scoped>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #4a90e2;
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.app-header h1 {
  margin: 0;
  font-size: 24px;
}

.app-main {
  flex: 1;
  padding: 20px;
  background-color: #f5f5f5;
}
</style>
