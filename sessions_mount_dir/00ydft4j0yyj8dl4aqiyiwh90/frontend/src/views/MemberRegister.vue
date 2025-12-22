<template>
  <div class="member-register">
    <h1>会员注册</h1>
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <label for="name">姓名</label>
        <input 
          type="text" 
          id="name" 
          v-model="formData.name" 
          required 
          placeholder="请输入您的姓名"
        />
      </div>
      
      <div class="form-group">
        <label for="phone">手机号</label>
        <input 
          type="tel" 
          id="phone" 
          v-model="formData.phone" 
          required 
          placeholder="请输入您的手机号"
          pattern="[0-9]{11}"
        />
      </div>
      
      <div class="form-group">
        <label for="email">邮箱</label>
        <input 
          type="email" 
          id="email" 
          v-model="formData.email" 
          required 
          placeholder="请输入您的邮箱"
        />
      </div>
      
      <button type="submit" class="submit-btn">注册</button>
    </form>
    
    <div v-if="successMessage" class="success-message">
      {{ successMessage }}
    </div>
    
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import axios from 'axios';

export default {
  name: 'MemberRegister',
  setup() {
    const formData = ref({
      name: '',
      phone: '',
      email: ''
    });
    
    const successMessage = ref('');
    const errorMessage = ref('');
    
    const submitForm = async () => {
      try {
        const response = await axios.post('/api/v1/members', formData.value);
        
        if (response.status === 201) {
          successMessage.value = '注册成功！';
          errorMessage.value = '';
          formData.value = { name: '', phone: '', email: '' };
        }
      } catch (error) {
        errorMessage.value = error.response?.data?.detail || '注册失败，请稍后重试';
        successMessage.value = '';
      }
    };
    
    return {
      formData,
      successMessage,
      errorMessage,
      submitForm
    };
  }
};
</script>

<style scoped>
.member-register {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn:hover {
  background-color: #369f73;
}

.success-message {
  margin-top: 20px;
  padding: 10px;
  background-color: #dff0d8;
  color: #3c763d;
  border-radius: 4px;
  text-align: center;
}

.error-message {
  margin-top: 20px;
  padding: 10px;
  background-color: #f2dede;
  color: #a94442;
  border-radius: 4px;
  text-align: center;
}
</style>