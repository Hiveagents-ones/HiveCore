<script setup>
import { ref } from 'vue'

defineProps({
  msg: String,
})

const count = ref(0)
</script>

<template>
  <h1>会员管理系统</h1>

  <div class="card">
    <h3>会员管理功能</h3>
    <ul>
      <li>会员注册</li>
      <li>会员查询</li>
      <li>资料修改</li>
      <li>会员删除</li>
    </ul>
  </div>

  <div class="card">
    <h3>课程预约功能</h3>
    <ul>
      <li>预约课程</li>
      <li>查看课程安排</li>
      <li>取消预约</li>
    </ul>
  </div>

</template>

<style scoped>
.card {
  margin: 20px 0;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
}

.card h3 {
  margin-top: 0;
}

.card ul {
  padding-left: 20px;
}
</style>