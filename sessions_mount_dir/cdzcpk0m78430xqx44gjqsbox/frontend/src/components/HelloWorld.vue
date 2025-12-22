<script setup>
import { ref } from 'vue'
import { useMemberStore } from '../stores/member'

const memberStore = useMemberStore()

defineProps({
  msg: String,
})

const count = ref(0)
</script>

<template>
  <h1>{{ msg }}</h1>

  <div class="card">
    <button type="button" @click="count++">count is {{ count }}</button>
    <p>
      Edit
      <code>components/HelloWorld.vue</code> to test HMR
    </p>
  </div>

  <div class="member-info">
    <h2>会员信息</h2>
    <div v-if="memberStore.currentMember">
      <p>姓名: {{ memberStore.currentMember.name }}</p>
      <p>电话: {{ memberStore.currentMember.phone }}</p>
      <p>会员卡状态: {{ memberStore.currentMember.card_status }}</p>
    </div>
    <div v-else>
      <p>暂无会员信息</p>
    </div>
  </div>

  <p class="read-the-docs">Click on the Vite and Vue logos to learn more</p>
</template>

<style scoped>
.read-the-docs {
  color: #888;
}

.member-info {
  margin-top: 2rem;
  padding: 1rem;
  border: 1px solid #eee;
  border-radius: 8px;
}

.member-info h2 {
  margin-bottom: 1rem;
}
</style>
