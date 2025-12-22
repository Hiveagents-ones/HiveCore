<template>
  <div class="member-form">
    <h2>会员注册</h2>
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <label for="name">姓名</label>
        <input v-model="form.name" id="name" type="text" placeholder="请输入姓名" required>
        <p v-if="errors.name" class="error">{{ errors.name }}</p>
      </div>

      <div class="form-group">
        <label for="phone">手机号</label>
        <input v-model="form.phone" id="phone" type="tel" placeholder="请输入11位手机号" required>
        <p v-if="errors.phone" class="error">{{ errors.phone }}</p>
      </div>

      <div class="form-group">
        <label for="email">邮箱（可选）</label>
        <input v-model="form.email" id="email" type="email" placeholder="请输入邮箱">
        <p v-if="errors.email" class="error">{{ errors.email }}</p>
      </div>

      <div class="form-group">
        <label for="healthInfo">健康信息</label>
        <textarea v-model="form.healthInfo" id="healthInfo" placeholder="请输入健康信息（必填）" required></textarea>
        <p v-if="errors.healthInfo" class="error">{{ errors.healthInfo }}</p>
      </div>

      <button type="submit" class="submit-btn">提交注册</button>
    </form>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';

const form = reactive({
  name: '',
  phone: '',
  email: '',
  healthInfo: ''
});

const errors = ref({});

const validate = () => {
  errors.value = {};

  // 姓名验证
  if (!form.name.trim()) {
    errors.value.name = '姓名不能为空';
  } else if (form.name.length < 2) {
    errors.value.name = '姓名至少2个字符';
  }

  // 手机号验证
  const phoneRegex = /^1[3-9]\d{9}$/;
  if (!form.phone.trim()) {
    errors.value.phone = '手机号不能为空';
  } else if (!phoneRegex.test(form.phone)) {
    errors.value.phone = '请输入有效的11位手机号';
  }

  // 邮箱验证
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (form.email && !emailRegex.test(form.email)) {
    errors.value.email = '请输入有效的邮箱格式';
  }

  // 健康信息验证
  if (!form.healthInfo.trim()) {
    errors.value.healthInfo = '健康信息不能为空';
  }

  return Object.keys(errors.value).length === 0;
};

const submitForm = () => {
  if (validate()) {
    console.log('表单提交数据:', form);
    // 实际项目中应调用API提交数据
    alert('注册成功！会员ID已生成');
  }
};
</script>

<style scoped>
.member-form {
  max-width: 500px;
  margin: 2rem auto;
  padding: 2rem;
  background: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

input,
textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
}

input:focus,
textarea:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 0.2rem rgba(0,123,255,0.25);
}

.error {
  color: #dc3545;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.submit-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  width: 100%;
  transition: background 0.3s;
}

.submit-btn:hover {
  background: #0069d9;
}
</style>