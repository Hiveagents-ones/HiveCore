<template>
  <div class="member-form">
    <h2>{{ formTitle }}</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="name">姓名</label>
        <input type="text" id="name" v-model="form.name" required />
      </div>
      <div class="form-group">
        <label for="contact">联系方式</label>
        <input type="text" id="contact" v-model="form.contact" required />
      </div>
      <div class="form-group">
        <label for="memberType">会员类型</label>
        <select id="memberType" v-model="form.member_type" required>
          <option value="普通会员">普通会员</option>
          <option value="高级会员">高级会员</option>
        </select>
      </div>
      <div class="form-group">
        <label for="validUntil">有效期</label>
        <input type="date" id="validUntil" v-model="form.valid_until" required />
      </div>
      <button type="submit">提交</button>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useMemberStore } from '@/stores/member';
import { storeToRefs } from 'pinia';

const route = useRoute();
const router = useRouter();
const memberStore = useMemberStore();
const { members } = storeToRefs(memberStore);

const form = reactive({
  id: null,
  name: '',
  contact: '',
  member_type: '普通会员',
  valid_until: ''
});

const formTitle = computed(() => {
  return form.id ? '编辑会员信息' : '新增会员信息';
});

const handleSubmit = async () => {
  if (form.id) {
    await memberStore.updateMember(form);
  } else {
    await memberStore.addMember(form);
  }
  router.push('/members');
};

if (route.params.id) {
  const member = members.value.find(m => m.id === parseInt(route.params.id));
  if (member) {
    Object.assign(form, member);
  }
}
</script>

<style scoped>
.member-form {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
}

input, select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

button {
  padding: 10px 15px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #0056b3;
}
</style>