<template>
  <form @submit.prevent="handleSubmit">
    <div class="form-group">
      <label for="name">姓名</label>
      <input id="name" v-model="form.name" type="text" required />
    </div>
    <div class="form-group">
      <label for="email">邮箱</label>
      <input id="email" v-model="form.email" type="email" required />
    </div>
    <div class="form-group">
      <label for="phone">联系电话</label>
      <input id="phone" v-model="form.phone" type="tel" required />
    </div>
    <div class="form-group">
      <label for="goal">健身目标</label>
      <textarea id="goal" v-model="form.goal" required></textarea>
    </div>
    <button type="submit">保存</button>
  </form>
</template>

<script>
import { updateMemberProfile } from '@/api/member';

export default {
  name: 'ProfileForm',
  props: {
    member: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      form: { ...this.member }
    };
  },
  methods: {
    async handleSubmit() {
      try {
        await updateMemberProfile(this.form);
        alert('信息更新成功！');
      } catch (error) {
        alert('更新失败，请重试。');
      }
    }
  }
};
</script>

<style scoped>
.form-group {
  margin-bottom: 15px;
}
label {
  display: block;
  margin-bottom: 5px;
}
input, textarea {
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
}
button {
  padding: 10px 15px;
  background-color: #42b983;
  color: white;
  border: none;
  cursor: pointer;
}
</style>