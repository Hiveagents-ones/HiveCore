<template>
  <div class="member-register">
    <h1>会员注册</h1>
    <form @submit.prevent="submitForm">
      <div class="form-group">


      <div class="form-group">
        <label for="gender">性别</label>
        <select id="gender" v-model="formData.gender" required>
          <option value="male">男</option>
          <option value="female">女</option>
          <option value="other">其他</option>
        </select>
      </div>
      <div class="form-group">
        <label for="birthday">生日</label>
        <input 
          type="date" 
          id="birthday" 
          v-model="formData.birthday" 
          required
        />
      </div>
      <div class="form-group">
        <label for="address">地址</label>
        <input 
          type="text" 
          id="address" 
          v-model="formData.address" 
          required
        />
      </div>
        <label for="name">姓名</label>
        <input 
          type="text" 
          id="name" 
          v-model="formData.name" 
          required
        />
      </div>
      
      <div class="form-group">
        <label for="email">邮箱</label>
        <input 
          type="email" 
          id="email" 
          v-model="formData.email" 
          required
        />
      </div>
      
      <div class="form-group">
        <label for="phone">电话</label>
        <input 
          type="tel" 
          id="phone" 
          v-model="formData.phone" 
          required
        />
      </div>
      
      <div class="form-group">
        <label for="joinDate">加入日期</label>
        <input 
          type="date" 
          id="joinDate" 
          v-model="formData.join_date" 
          required
        />
      </div>
      
      <button type="submit" class="submit-btn">注册</button>
    </form>
  </div>
</template>

<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { createMember } from '@/api/members';

export default {
  name: 'MemberRegister',
  setup() {
    const router = useRouter();
    const formData = ref({
      name: '',
      email: '',
      phone: '',
      address: '',
      gender: 'male',
      birthday: '',
      join_date: new Date().toISOString().split('T')[0],
      emergency_contact: '',
      emergency_phone: ''
    });

    const submitForm = async () => {
      try {
        await createMember(formData.value);
        alert('会员注册成功！');
        router.push({ name: 'MemberList' });
      } catch (error) {
        console.error('注册失败:', error);
        alert('注册失败，请重试');
      }
    };

    return {
      formData,
      submitForm
    };
  }
};
</script>

<style scoped>
.member-register {
  max-width: 600px;
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
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn:hover {
  background-color: #45a049;
}
</style>