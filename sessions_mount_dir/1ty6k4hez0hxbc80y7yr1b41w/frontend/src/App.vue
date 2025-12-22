<template>
  <div id="app">
    <nav>
      <router-link to="/members">会员档案</router-link> |
      <router-link to="/courses">课程预约</router-link> |
      <router-link to="/coaches">教练排班</router-link> |
      <router-link to="/payments">收费管理</router-link>
    </nav>
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App',
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

nav {
  padding: 20px;
}

nav a {
  font-weight: bold;
  color: #2c3e50;
  margin: 0 10px;
}

nav a.router-link-exact-active {
  color: #42b983;
}
</style>